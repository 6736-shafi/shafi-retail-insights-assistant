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
REPO_NAME="retail-repo"

echo ""
echo "🚀 Starting Deployment..."
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "App Name: $APP_NAME"
echo "Repository: $REPO_NAME"
echo "========================================================"

# 0. Set Project
gcloud config set project $PROJECT_ID

# 1. Enable Services
echo "Enabling Cloud Run and Artifact Registry APIs..."
gcloud services enable run.googleapis.com artifactregistry.googleapis.com

# 2. Create Artifact Registry Repository (if not exists)
echo "Checking/Creating Artifact Registry Repository..."
if ! gcloud artifacts repositories describe $REPO_NAME --location=$REGION --project=$PROJECT_ID > /dev/null 2>&1; then
    gcloud artifacts repositories create $REPO_NAME \
        --repository-format=docker \
        --location=$REGION \
        --description="Docker repository for Retail Insights Assistant"
    echo "✅ Repository created."
else
    echo "✅ Repository already exists."
fi

# 3. Build and Push Image
echo "Configuring Docker..."
gcloud auth configure-docker $REGION-docker.pkg.dev --quiet

IMAGE_URI="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$APP_NAME:v1"

echo "Building Docker Image..."
# Build for linux/amd64 (Cloud Run requirement)
docker build --platform linux/amd64 -t $IMAGE_URI .

echo "Pushing Docker Image to Artifact Registry..."
docker push $IMAGE_URI

# 4. Deploy to Cloud Run
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
    --image $IMAGE_URI \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --set-env-vars GOOGLE_API_KEY="$API_KEY" \
    --port 8501 \
    --memory 2Gi \
    --cpu 1

echo "========================================================"
echo "✅ Deployment Complete!"
echo "Check the URL above to access your app."
echo "========================================================"
