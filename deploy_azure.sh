#!/bin/bash

# Azure Deployment Script for Retail Insights Assistant

echo "========================================================"
echo "   Azure Deployment Script: Retail Insights Assistant   "
echo "========================================================"

# Check if logged in
echo "Checking Azure login status..."
az account show > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ You are not logged in."
    echo "👉 Please run 'az login' in your terminal and then re-run this script."
    exit 1
fi
echo "✅ Logged in."

# Configuration
echo ""
if [ -z "$RG_NAME" ]; then
    read -p "Enter a name for your Resource Group (default: RetailInsightsGroup): " RG_NAME
fi
RG_NAME=${RG_NAME:-RetailInsightsGroup}

if [ -z "$LOCATION" ]; then
    read -p "Enter a location (default: eastus): " LOCATION
fi
LOCATION=${LOCATION:-eastus}

# Generate unique names
SUFFIX=$RANDOM
ACR_NAME="retailinsightsacr$SUFFIX"
APP_NAME="retail-insights-app-$SUFFIX"
PLAN_NAME="RetailInsightsPlan"

echo ""
echo "🚀 Starting Deployment..."
echo "Resource Group: $RG_NAME"
echo "Location: $LOCATION"
echo "ACR Name: $ACR_NAME"
echo "App Name: $APP_NAME"
echo "========================================================"

# 1. Create Resource Group
echo "Creating Resource Group..."
az group create --name $RG_NAME --location $LOCATION

# 2. Create ACR
echo "Creating Azure Container Registry ($ACR_NAME)..."
az acr create --resource-group $RG_NAME --name $ACR_NAME --sku Basic --admin-enabled true

# 3. Build and Push Image
echo "Logging into ACR..."
az acr login --name $ACR_NAME

echo "Building Docker Image..."
# Build for linux/amd64 to ensure compatibility with Azure App Service
docker build --platform linux/amd64 -t $ACR_NAME.azurecr.io/retail-assistant:v1 .

echo "Pushing Docker Image to ACR..."
docker push $ACR_NAME.azurecr.io/retail-assistant:v1

# 4. Create App Service
echo "Creating App Service Plan ($PLAN_NAME)..."
az appservice plan create --name $PLAN_NAME --resource-group $RG_NAME --sku B1 --is-linux

echo "Creating Web App ($APP_NAME)..."
az webapp create --resource-group $RG_NAME --plan $PLAN_NAME --name $APP_NAME --deployment-container-image-name $ACR_NAME.azurecr.io/retail-assistant:v1

# 5. Configure Settings
echo "Configuring Environment Variables..."
if [ -z "$API_KEY" ]; then
    read -s -p "Enter your GOOGLE_API_KEY: " API_KEY
    echo ""
fi

az webapp config appsettings set --resource-group $RG_NAME --name $APP_NAME --settings GOOGLE_API_KEY="$API_KEY" WEBSITES_PORT=8501

echo "========================================================"
echo "✅ Deployment Complete!"
echo "🌍 Your app is live at: https://$APP_NAME.azurewebsites.net"
echo "========================================================"
