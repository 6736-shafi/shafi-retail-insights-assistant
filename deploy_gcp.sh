#!/bin/bash

# GCP Deployment Script for Retail Insights Assistant

echo "========================================================"
echo "   GCP Deployment Script: Retail Insights Assistant     "
echo "========================================================"

# Check if logged in
echo "Checking gcloud login status..."
gcloud auth list --filter=status:ACTIVE --format="value(account)" > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ You are not logged in."
    echo "👉 Please run 'gcloud auth login' in your terminal and then re-run this script."
    exit 1
fi
echo "✅ Logged in."

# Configuration
echo ""
if [ -z "$PROJECT_ID" ]; then
    read -p "Enter your GCP Project ID: " PROJECT_ID
fi

if [ -z "$REGION" ]; then
    read -p "Enter a region (default: us-central1): " REGION
fi
REGION=${REGION:-us-central1}

APP_NAME="retail-assistant"

echo ""
echo "🚀 Starting Deployment..."
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "App Name: $APP_NAME"
echo "========================================================"

# 0. Set Project
gcloud config set project $PROJECT_ID

# 1. Enable Services
echo "Enabling Cloud Run and Container Registry APIs..."
gcloud services enable run.googleapis.com containerregistry.googleapis.com

# 2. Build and Push Image
echo "Configuring Docker..."
gcloud auth configure-docker --quiet

echo "Building Docker Image..."
# Build for linux/amd64
docker build --platform linux/amd64 -t gcr.io/$PROJECT_ID/$APP_NAME:v1 .

echo "Pushing Docker Image to GCR..."
docker push gcr.io/$PROJECT_ID/$APP_NAME:v1

# 3. Deploy to Cloud Run
echo "Deploying to Cloud Run..."

# Get API Key
if [ -z "$API_KEY" ]; then
    # Try to read from .env
    if [ -f .env ]; then
        API_KEY=$(grep GOOGLE_API_KEY .env | cut -d '=' -f2)
    fi
    
    if [ -z "$API_KEY" ]; then
        read -s -p "Enter your GOOGLE_API_KEY: " API_KEY
        echo ""
    fi
fi

gcloud run deploy $APP_NAME \
    --image gcr.io/$PROJECT_ID/$APP_NAME:v1 \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --set-env-vars GOOGLE_API_KEY="$API_KEY" \
    --port 8501

echo "========================================================"
echo "✅ Deployment Complete!"
echo "Check the URL above to access your app."
echo "========================================================"
