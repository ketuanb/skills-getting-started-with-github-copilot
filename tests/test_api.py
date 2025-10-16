"""
Test suite for Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities
import json


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities data before each test"""
    # Store original activities
    original_activities = activities.copy()
    
    # Reset to a known state for testing
    activities.clear()
    activities.update({
        "Test Club": {
            "description": "A test club for testing purposes",
            "schedule": "Test Schedule",
            "max_participants": 5,
            "participants": ["test1@mergington.edu", "test2@mergington.edu"]
        },
        "Empty Club": {
            "description": "An empty club with no participants",
            "schedule": "Empty Schedule",
            "max_participants": 10,
            "participants": []
        }
    })
    
    yield
    
    # Restore original activities after test
    activities.clear()
    activities.update(original_activities)


class TestRootEndpoint:
    """Test the root endpoint"""
    
    def test_root_redirects_to_static_index(self, client):
        """Test that root endpoint redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307  # Temporary redirect
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Test the activities endpoint"""
    
    def test_get_activities_success(self, client, reset_activities):
        """Test successful retrieval of activities"""
        response = client.get("/activities")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "Test Club" in data
        assert "Empty Club" in data
        
        # Verify structure of returned data
        test_club = data["Test Club"]
        assert test_club["description"] == "A test club for testing purposes"
        assert test_club["schedule"] == "Test Schedule"
        assert test_club["max_participants"] == 5
        assert len(test_club["participants"]) == 2
        assert "test1@mergington.edu" in test_club["participants"]
        assert "test2@mergington.edu" in test_club["participants"]
        
        # Verify empty club
        empty_club = data["Empty Club"]
        assert len(empty_club["participants"]) == 0


class TestSignupEndpoint:
    """Test the signup endpoint"""
    
    def test_signup_success(self, client, reset_activities):
        """Test successful signup for an activity"""
        email = "newstudent@mergington.edu"
        activity_name = "Test Club"
        
        response = client.post(f"/activities/{activity_name}/signup?email={email}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == f"Signed up {email} for {activity_name}"
        
        # Verify the participant was actually added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity_name]["participants"]
    
    def test_signup_activity_not_found(self, client, reset_activities):
        """Test signup for non-existent activity"""
        email = "student@mergington.edu"
        activity_name = "NonExistent Club"
        
        response = client.post(f"/activities/{activity_name}/signup?email={email}")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_signup_already_registered(self, client, reset_activities):
        """Test signup when student is already registered"""
        email = "test1@mergington.edu"  # Already in Test Club
        activity_name = "Test Club"
        
        response = client.post(f"/activities/{activity_name}/signup?email={email}")
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Student is already signed up"
    
    def test_signup_empty_club(self, client, reset_activities):
        """Test signup for a club with no existing participants"""
        email = "newstudent@mergington.edu"
        activity_name = "Empty Club"
        
        response = client.post(f"/activities/{activity_name}/signup?email={email}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == f"Signed up {email} for {activity_name}"
        
        # Verify the participant was added to previously empty club
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity_name]["participants"]
        assert len(activities_data[activity_name]["participants"]) == 1


class TestUnregisterEndpoint:
    """Test the unregister endpoint"""
    
    def test_unregister_success(self, client, reset_activities):
        """Test successful unregistration from an activity"""
        email = "test1@mergington.edu"  # Already in Test Club
        activity_name = "Test Club"
        
        response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == f"Unregistered {email} from {activity_name}"
        
        # Verify the participant was actually removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data[activity_name]["participants"]
        assert len(activities_data[activity_name]["participants"]) == 1  # Only test2 should remain
    
    def test_unregister_activity_not_found(self, client, reset_activities):
        """Test unregister from non-existent activity"""
        email = "student@mergington.edu"
        activity_name = "NonExistent Club"
        
        response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_unregister_not_registered(self, client, reset_activities):
        """Test unregister when student is not registered"""
        email = "notregistered@mergington.edu"
        activity_name = "Test Club"
        
        response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Student is not signed up for this activity"
    
    def test_unregister_from_empty_club(self, client, reset_activities):
        """Test unregister from club with no participants"""
        email = "nobody@mergington.edu"
        activity_name = "Empty Club"
        
        response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"] == "Student is not signed up for this activity"


class TestEmailHandling:
    """Test various email formats and edge cases"""
    
    def test_signup_with_special_characters_in_email(self, client, reset_activities):
        """Test signup with special characters in email"""
        email = "test.user+tag@mergington.edu"
        activity_name = "Empty Club"
        
        # URL encode the email to handle special characters properly
        from urllib.parse import quote
        encoded_email = quote(email)
        
        response = client.post(f"/activities/{activity_name}/signup?email={encoded_email}")
        
        assert response.status_code == 200
        
        # Verify the email was stored correctly
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity_name]["participants"]
    
    def test_url_encoded_email(self, client, reset_activities):
        """Test signup with URL-encoded email"""
        email = "test%40mergington.edu"  # URL encoded @
        activity_name = "Empty Club"
        
        response = client.post(f"/activities/{activity_name}/signup?email={email}")
        
        assert response.status_code == 200


class TestActivityNameHandling:
    """Test various activity name formats and edge cases"""
    
    def test_activity_name_with_spaces(self, client, reset_activities):
        """Test activity names with spaces (URL encoded)"""
        email = "student@mergington.edu"
        activity_name = "Test Club"  # Has space
        
        # URL encode the activity name
        encoded_name = activity_name.replace(" ", "%20")
        response = client.post(f"/activities/{encoded_name}/signup?email={email}")
        
        assert response.status_code == 200


class TestIntegrationScenarios:
    """Test complete workflows and edge cases"""
    
    def test_signup_and_unregister_workflow(self, client, reset_activities):
        """Test complete signup and unregister workflow"""
        email = "workflow@mergington.edu"
        activity_name = "Empty Club"
        
        # Step 1: Sign up
        signup_response = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Step 2: Verify registration
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity_name]["participants"]
        
        # Step 3: Unregister
        unregister_response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        assert unregister_response.status_code == 200
        
        # Step 4: Verify unregistration
        activities_response_final = client.get("/activities")
        activities_data_final = activities_response_final.json()
        assert email not in activities_data_final[activity_name]["participants"]
    
    def test_multiple_students_same_activity(self, client, reset_activities):
        """Test multiple students signing up for the same activity"""
        activity_name = "Empty Club"
        emails = ["student1@mergington.edu", "student2@mergington.edu", "student3@mergington.edu"]
        
        # Sign up multiple students
        for email in emails:
            response = client.post(f"/activities/{activity_name}/signup?email={email}")
            assert response.status_code == 200
        
        # Verify all are registered
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        for email in emails:
            assert email in activities_data[activity_name]["participants"]
        
        assert len(activities_data[activity_name]["participants"]) == 3
    
    def test_student_signup_multiple_activities(self, client, reset_activities):
        """Test one student signing up for multiple activities"""
        email = "busy@mergington.edu"
        activities_list = ["Test Club", "Empty Club"]
        
        # Sign up for multiple activities
        for activity_name in activities_list:
            response = client.post(f"/activities/{activity_name}/signup?email={email}")
            assert response.status_code == 200
        
        # Verify registration in all activities
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        for activity_name in activities_list:
            assert email in activities_data[activity_name]["participants"]


class TestDataConsistency:
    """Test data consistency and validation"""
    
    def test_participant_count_consistency(self, client, reset_activities):
        """Test that participant counts remain consistent"""
        activity_name = "Test Club"
        
        # Get initial count
        initial_response = client.get("/activities")
        initial_data = initial_response.json()
        initial_count = len(initial_data[activity_name]["participants"])
        
        # Add a participant
        email = "newparticipant@mergington.edu"
        signup_response = client.post(f"/activities/{activity_name}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Verify count increased
        after_signup_response = client.get("/activities")
        after_signup_data = after_signup_response.json()
        after_signup_count = len(after_signup_data[activity_name]["participants"])
        assert after_signup_count == initial_count + 1
        
        # Remove the participant
        unregister_response = client.delete(f"/activities/{activity_name}/unregister?email={email}")
        assert unregister_response.status_code == 200
        
        # Verify count returned to original
        final_response = client.get("/activities")
        final_data = final_response.json()
        final_count = len(final_data[activity_name]["participants"])
        assert final_count == initial_count