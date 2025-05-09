from app import app
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from schema.user import User
from unittest.mock import patch, MagicMock
import pytest

client = TestClient(app)

class TestApp:

    def test_create_user_1(self):
        """
        Test case for creating a user when the created_user is None.
        This test verifies that an HTTPException with status code 500 is raised
        when the database operation fails to return a created user.
        """
        # Mock user data
        test_user = User(username="testuser", email="test@example.com", password="testpass")

        # Mock the database operations
        def mock_insert_one(user_dict):
            class MockResult:
                inserted_id = "mock_id"
            return MockResult()

        def mock_find_one():
            return None  # Simulate that no user was found after insertion

        # Apply the mocks
        app.db.get_collection("users").insert_one = mock_insert_one
        app.db.get_collection("users").find_one = mock_find_one

        # Make the request and check the response
        with pytest.raises(HTTPException) as exc_info:
            response = client.post("/users/", json=test_user.model_dump())

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert exc_info.value.detail == "Failed to create user"

    def test_create_user_2(self):
        """
        Test creating a user when the user is successfully inserted into the database.
        This test verifies that when a valid user is provided, the create_user function
        inserts the user into the database and returns the created user object.
        """
        test_user = User(username="testuser", email="test@example.com", password="testpassword")
        response = client.post("/users/", json=test_user.model_dump())

        assert response.status_code == status.HTTP_201_CREATED
        created_user = response.json()
        assert created_user["username"] == test_user.username
        assert created_user["email"] == test_user.email
        assert "password" not in created_user  # Ensure the password is not returned

    def test_create_user_database_error(self):
        """
        Test that create_user raises an HTTPException with status code 500
        when there's a database error (simulated by mocking the database operation).
        """
        valid_user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User"
        }

        # Mock the database insert operation to simulate a failure
        def mock_insert_one(*args, **kwargs):
            class MockResult:
                @property
                def inserted_id(self):
                    return None
            return MockResult()

        # Apply the mock
        app.db.get_collection("users").insert_one = mock_insert_one

        response = client.post("/users/", json=valid_user_data)
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Failed to create user"

        # Reset the mock to avoid affecting other tests
        app.db.get_collection("users").insert_one = lambda x: x

    def test_create_user_validation_error(self):
        """
        Test that create_user raises an HTTPException with status code 422
        when a ValidationError occurs due to invalid user data.
        """
        invalid_user_data = {
            "username": "testuser",
            "email": "invalid_email",  # Invalid email format
            "full_name": "Test User"
        }

        response = client.post("/users/", json=invalid_user_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "value is not a valid email address" in response.json()["detail"]

    def test_delete_user_1(self):
        """
        Test deleting an existing user.

        This test ensures that when a valid email is provided for an existing user,
        the user is successfully deleted from the database and the correct success
        message is returned.
        """
        test_email = "test@example.com"
        mock_user = {"email": test_email}

        with patch("app.db.get_collection") as mock_get_collection:
            mock_find = MagicMock()
            mock_find.return_value = [mock_user]
            mock_get_collection.return_value.find = mock_find

            mock_delete_one = MagicMock()
            mock_get_collection.return_value.delete_one = mock_delete_one

            response = client.delete(f"/users/{test_email}")

            assert response.status_code == 200
            assert response.json() == {"message": f"User with email {test_email} deleted successfully"}

            mock_get_collection.assert_called_with("users")
            mock_find.assert_called_with({"email": test_email})
            mock_delete_one.assert_called_with({"email": test_email})

    def test_delete_user_database_error(self):
        """
        Test delete_user when a database error occurs.
        This tests the edge case where an unexpected exception is raised during the database operation.
        """
        with patch('app.db.get_collection') as mock_get_collection:
            mock_find = MagicMock()
            mock_find.side_effect = Exception("Database connection error")
            mock_get_collection.return_value.find = mock_find

            response = client.delete("/users/user@example.com")

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Database connection error" in response.json()["detail"]

    def test_delete_user_nonexistent(self):
        """
        Test deleting a user that doesn't exist in the database.

        This test case verifies that the delete_user function raises a 404 Not Found
        error when attempting to delete a user with an email that doesn't exist in
        the database.
        """
        non_existent_email = "nonexistent@example.com"
        response = client.delete(f"/users/{non_existent_email}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "No user found"}

    def test_delete_user_not_found(self):
        """
        Test delete_user when the user is not found in the database.
        This tests the edge case where the email provided does not match any user.
        """
        with patch('app.db.get_collection') as mock_get_collection:
            mock_find = MagicMock()
            mock_find.return_value = []
            mock_get_collection.return_value.find = mock_find

            response = client.delete("/users/nonexistent@example.com")

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert response.json() == {"detail": "No user found"}

    def test_get_user_1(self):
        """
        Test get_user when no user is found.
        This test verifies that the get_user function returns a 404 Not Found
        status code and the correct error message when no user matches the search criteria.
        """
        response = client.get("/users/nonexistentuser")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "No user found"}

    def test_get_user_2(self):
        """
        Test the get_user function when users are found.

        This test verifies that the get_user function returns a list of users
        when at least one user matches the search criteria. It checks that:
        1. The response status code is 200 (OK)
        2. The response body is a non-empty list
        3. Each user in the response has the expected structure
        """
        search = "test@example.com"
        response = client.get(f"/users/{search}")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) > 0
        for user in response.json():
            assert "username" in user
            assert "email" in user

    def test_get_user_internal_server_error(self):
        """
        Test the get_user function when an unexpected exception occurs.
        This tests the explicit error handling for a 500 Internal Server Error scenario.
        """
        with patch('app.db.get_collection') as mock_get_collection:
            mock_get_collection.side_effect = Exception("Unexpected database error")

            response = client.get("/users/test@example.com")

            assert response.status_code == 500
            assert response.json() == {"detail": "Unexpected database error"}

    def test_get_user_not_found(self):
        """
        Test the get_user function when no user is found for the given search criteria.
        This tests the explicit error handling for a 404 Not Found scenario.
        """
        with patch('app.db.get_collection') as mock_get_collection:
            mock_find = MagicMock()
            mock_find.return_value = []
            mock_get_collection.return_value.find = mock_find

            response = client.get("/users/nonexistent@example.com")

            assert response.status_code == 404
            assert response.json() == {"detail": "No user found"}

    def test_get_users_database_error(self):
        """
        Test the get_users endpoint when a database error occurs.
        This test verifies that the method handles exceptions and returns a 500 Internal Server Error.
        """
        with patch('app.db.get_collection') as mock_get_collection:
            mock_get_collection.return_value.find.side_effect = Exception("Database error")

            response = client.get("/users/")

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Database error" in response.json()["detail"]

    def test_get_users_returns_list_of_users(self):
        """
        Test that the get_users endpoint returns a list of users successfully.

        This test verifies that:
        1. The endpoint returns 200 OK status code
        2. The response contains a list of users
        3. Each user in the list has the expected structure (id, username, email)
        """
        response = client.get("/users/")
        assert response.status_code == 200
        users = response.json()
        assert isinstance(users, list)
        for user in users:
            assert "id" in user
            assert "username" in user
            assert "email" in user

    def test_root_1(self):
        """
        Test the root endpoint to ensure it returns the correct welcome message.

        This test verifies that the root endpoint ("/") responds with a 200 status code
        and returns the expected JSON response containing the welcome message.
        """
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "Welcome to the Fast API with MongoDB !"}

    def test_root_success(self):
        """
        Test that the root endpoint returns the expected message.
        """
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "Welcome to the Fast API with MongoDB !"}
