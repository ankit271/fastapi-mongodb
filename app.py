import os
from fastapi import FastAPI, HTTPException, status
from pydantic import ValidationError
from pymongo import MongoClient
from schema.user import User, UserResponse

app = FastAPI(
    title="Fast API with MongoDB",
    summary="A sample application showing how to use FastAPI to add a ReST API to a MongoDB collection.",
)
db_url: str = os.environ["MONGODB_URL"]
client: MongoClient = MongoClient(db_url)

db = client.get_database("fastapi-mongodb")
collections = db.list_collection_names()
print("Collections in the database:", collections)

data = db.get_collection("fastapi-mongodb").find_one({"info": "Mongo DB"})
print("Data in the collection:", data)


@app.get("/")
async def root():
    return {"message": "Welcome to the Fast API with MongoDB !"}


@app.post("/users/", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(user: User):
    try:
        # Convert the user model to a dictionary for MongoDB
        user_dict = user.model_dump(by_alias=True)

        # Insert the user into the database
        result = db.get_collection("users").insert_one(user_dict)

        # Get the created user from the database to return
        created_user = db.get_collection("users").find_one({"_id": result.inserted_id})

        if created_user is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="Failed to create user")

        # Return the created user
        return User.model_validate(created_user)

    except ValidationError as err:
        # Properly handle validation errors
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=str(err))
    except Exception as err:
        # Handle other errors
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=str(err))


@app.get("/users/", response_model=list[UserResponse], status_code=status.HTTP_200_OK)
async def get_users():
    try:
        # Fetch all users from the database
        users = db.get_collection("users").find()
        user_list = [UserResponse.model_validate(user) for user in users]

        return user_list

    except Exception as err:
        # Handle other errors
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=str(err))


@app.get("/users/{search}", response_model=list[UserResponse], status_code=status.HTTP_200_OK)
async def get_user(search: str):
    try:
        # Fetch all users from the database
        users = db.get_collection("users").find({"$or": [{"email": search}, {"username": search}]})

        user_list = [UserResponse.model_validate(user) for user in users]

        if not user_list:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="No user found")

        return user_list

    except HTTPException as http_err:
        raise http_err

    except Exception as err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=str(err))


@app.delete("/users/{email}", status_code=status.HTTP_200_OK)
async def delete_user(email: str):
    try:
        # Fetch all users from the database
        users = db.get_collection("users").find({"email": email})

        user_list = [user for user in users]

        if not user_list:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="No user found")
        else:
            db.get_collection("users").delete_one({"email": email})
            return {"message": f"User with email {email} deleted successfully"}

    except HTTPException as http_err:
        raise http_err

    except Exception as err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=str(err))
