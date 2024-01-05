Simple streamlit app based using playwright and pandas to show search results for multiple czech mtg card selling sites.

# Step 1: Login to Docker Hub
docker login -u your_dockerhub_username -p your_dockerhub_password

# Step 2: Tag your local image
docker tag mtgstockandprice_web:latest your_dockerhub_username/mtgstockandprice:latest

# Step 3: Push the tagged image to Docker Hub
docker push your_dockerhub_username/mtgstockandprice:latest
