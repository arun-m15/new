
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import cv2
import numpy as np
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import requests
import os
from pprint import pprint

# Create FastAPI instance
app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Welcome to Smart Agriculture Assistant API"}

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Security configuration
SECRET_KEY = "your-secret-key"  # Move to environment variables
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
OPENWEATHER_API_KEY = "your-api-key"  # Move to environment variables

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Mock database - Replace with real database in production
users_db = {}

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def analyze_leaf_image(image_path: str):
    try:
        # Check if file exists
        if not os.path.exists(image_path):
            raise HTTPException(status_code=404, detail=f"Image file not found at {image_path}")
            
        # Load and preprocess image
        img = cv2.imread(image_path)
        if img is None:
            raise HTTPException(status_code=400, detail="Failed to process image. Ensure it's a valid image file.")
        
        # Convert to HSV for better color analysis
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")
    
    # Simple analysis based on color distribution
    green_lower = np.array([25, 40, 40])
    green_upper = np.array([85, 255, 255])
    mask = cv2.inRange(hsv, green_lower, green_upper)
    
    # Calculate green percentage
    green_ratio = np.sum(mask) / (mask.shape[0] * mask.shape[1] * 255)
    
    # Basic health assessment
    if green_ratio > 0.7:
        health = "Healthy"
    elif green_ratio > 0.4:
        health = "Moderate"
    else:
        health = "Unhealthy"
    
    return {
        "health_status": health,
        "green_percentage": round(green_ratio * 100, 2),
        "recommendations": get_recommendations(health)
    }

def get_recommendations(health_status: str):
    recommendations = {
        "Healthy": ["Continue current care regime", "Regular watering"],
        "Moderate": ["Increase watering", "Check for pests", "Consider fertilization"],
        "Unhealthy": ["Urgent attention needed", "Check for disease", "Adjust sunlight exposure"]
    }
    return recommendations.get(health_status, [])

@app.post("/api/register")
async def register(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username in users_db:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = pwd_context.hash(form_data.password)
    users_db[form_data.username] = {
        "username": form_data.username,
        "hashed_password": hashed_password
    }
    return {"message": "User created successfully"}

@app.post("/api/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = users_db.get(form_data.username)
    if not user or not pwd_context.verify(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    access_token = create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/analyze-leaf")
async def analyze_leaf(file: UploadFile = File(...), token: str = Depends(oauth2_scheme)):
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    try:
        # Verify token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401)
    except JWTError:
        raise HTTPException(status_code=401)

    # Save and analyze image
    file_path = f"uploads/{file.filename}"
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # Analyze the leaf image
    result = analyze_leaf_image(file_path)
    # Pretty print the results for debugging
    pprint(result)
    return result

@app.get("/api/weather/{city}")
async def get_weather(city: str):
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={OPENWEATHER_API_KEY}"
    response = requests.get(url)
    return response.json()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
