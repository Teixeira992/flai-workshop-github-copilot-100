"""
Tests for the High School Management System API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities
import copy


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original activities data
    original_activities = copy.deepcopy(activities)
    
    yield
    
    # Reset activities data after each test
    activities.clear()
    activities.update(original_activities)


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root endpoint redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        
        # Verify we have activities
        assert len(data) > 0
        
        # Verify structure of activities
        assert "Basketball Team" in data
        assert "description" in data["Basketball Team"]
        assert "schedule" in data["Basketball Team"]
        assert "max_participants" in data["Basketball Team"]
        assert "participants" in data["Basketball Team"]
    
    def test_get_activities_response_format(self, client):
        """Test that activities response has correct format"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        
        # Test a specific activity has all required fields
        basketball = data.get("Basketball Team")
        assert basketball is not None
        assert isinstance(basketball["description"], str)
        assert isinstance(basketball["schedule"], str)
        assert isinstance(basketball["max_participants"], int)
        assert isinstance(basketball["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_for_valid_activity(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Basketball Team/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Signed up newstudent@mergington.edu for Basketball Team"
        
        # Verify student was added to participants
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newstudent@mergington.edu" in activities_data["Basketball Team"]["participants"]
    
    def test_signup_for_nonexistent_activity(self, client):
        """Test signup for an activity that doesn't exist"""
        response = client.post(
            "/activities/Nonexistent Activity/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_signup_duplicate_student(self, client):
        """Test that a student cannot sign up twice for the same activity"""
        email = "duplicate@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(
            "/activities/Drama Club/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(
            "/activities/Drama Club/signup",
            params={"email": email}
        )
        assert response2.status_code == 400
        data = response2.json()
        assert data["detail"] == "Student already signed up for this activity"
    
    def test_signup_multiple_activities(self, client):
        """Test that a student can sign up for multiple different activities"""
        email = "multitasker@mergington.edu"
        
        # Sign up for first activity
        response1 = client.post(
            "/activities/Basketball Team/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Sign up for second activity
        response2 = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response2.status_code == 200
        
        # Verify student is in both activities
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data["Basketball Team"]["participants"]
        assert email in activities_data["Chess Club"]["participants"]


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_from_activity(self, client):
        """Test successful unregistration from an activity"""
        # First sign up a student
        email = "student@mergington.edu"
        client.post(
            "/activities/Swimming Club/signup",
            params={"email": email}
        )
        
        # Now unregister
        response = client.delete(
            "/activities/Swimming Club/unregister",
            params={"email": email}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Unregistered student@mergington.edu from Swimming Club"
        
        # Verify student was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data["Swimming Club"]["participants"]
    
    def test_unregister_from_nonexistent_activity(self, client):
        """Test unregistration from an activity that doesn't exist"""
        response = client.delete(
            "/activities/Nonexistent Activity/unregister",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_unregister_student_not_registered(self, client):
        """Test unregistration of a student who is not registered"""
        response = client.delete(
            "/activities/Art Workshop/unregister",
            params={"email": "notregistered@mergington.edu"}
        )
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Student is not registered for this activity"
    
    def test_unregister_existing_participant(self, client):
        """Test unregistering a student who was already in the activity"""
        # james@mergington.edu is already in Basketball Team
        response = client.delete(
            "/activities/Basketball Team/unregister",
            params={"email": "james@mergington.edu"}
        )
        assert response.status_code == 200
        
        # Verify student was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "james@mergington.edu" not in activities_data["Basketball Team"]["participants"]


class TestActivityNameEncoding:
    """Tests for activities with special characters in names"""
    
    def test_signup_with_encoded_activity_name(self, client):
        """Test signup with URL-encoded activity name"""
        response = client.post(
            "/activities/Programming%20Class/signup",
            params={"email": "coder@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Programming Class" in data["message"]
