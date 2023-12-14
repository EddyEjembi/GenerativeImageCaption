from dotenv import load_dotenv
import os
from array import array
from PIL import Image, ImageDraw
import time
from datetime import datetime, timedelta
import threading
from matplotlib import pyplot as plt
import numpy as np
from flask import Flask, request, jsonify
import cloudinary.uploader
from cloudinary import api
import openai

app = Flask(__name__)

openai.api_type = "azure"
openai.api_base = "https://generativecaption.openai.azure.com/"
openai.api_version = "2023-07-01-preview"

# import namespaces
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
from msrest.authentication import CognitiveServicesCredentials

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
MAX_FILE_AGE_SECONDS = 5 * 60  # 30 minutes in seconds

cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
)

@app.route('/analyze', methods=["POST", "GET"])
def main():
    global cv_client

    try:
        # Get Configuration Settings
        load_dotenv()
        cog_endpoint = os.environ.get('COG_SERVICE_ENDPOINT') #os.getenv
        cog_key = os.environ.get('COG_SERVICE_KEY')
        openai.api_key = os.environ.get("OPENAI_API_KEY")


        # Get image
        file = request.files.get("image")

        # Check if the user selected a file
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        
        # Read the file content
        file_content = file.read()

        # Upload the file to Cloudinary
        upload_result = cloudinary.uploader.upload(file_content, public_id=file.filename, folder="ImageCaption")

        # use Cloudinary URL in image processing code
        image_file = upload_result['secure_url']


        """# Save the file to a specific location
        file_path = 'uploads/' + image_file.filename
        image_file.save(file_path)"""

        if image_file:

            #image_file = 'person.jpg'

            message = request.form.get('prompt', 'Write creative caption for this image')
            #message = input("enter a prompt (optional): ")

            # Authenticate Azure AI Vision client
            credential = CognitiveServicesCredentials(cog_key) 
            cv_client = ComputerVisionClient(cog_endpoint, credential)

            #content = 'content' #file content
            desc_list = [ ]
            content = " "


            # Analyze image
            AnalyzeImage(file, image_file, desc_list)

            #Generate Captions
            caption = GenerateCaption(content, desc_list, message)

            # Generate thumbnail
            #GetThumbnail(image_file)

            # Start a thread for delayed image deletion
            # Get a list of all resources in the specified folder
            resources = api.resources(type="upload", prefix="ImageCaption")

            # Print the public_ids of all files in the folder
            for resource in resources["resources"]:
                print(resource["public_id"])
                delete_thread = threading.Thread(target=delete_image, args=(resource['public_id'],resource['created_at']))
                delete_thread.start()

            response = {"response": caption}
            return jsonify(response), 200
        else:
            return jsonify({"error": "No image file provided!"}), 400

    except Exception as ex:
        print(ex)
        return jsonify({"error": str(ex)}), 500

"""def cleanup_expired_files():
    current_time = time.time()
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file_age = current_time - os.path.getmtime(file_path)
        if file_age > MAX_FILE_AGE_SECONDS:
            os.remove(file_path)"""

def delete_image(public_id, created_time):
    try:
        # Parse the timestamp string into a datetime object
        created_at = datetime.strptime(created_time, "%Y-%m-%dT%H:%M:%SZ")

        # Calculate the time difference between now and the created timestamp
        time_difference = datetime.utcnow() - created_at

        # Set the maximum age threshold (e.g., 30 minutes)
        max_age_threshold = timedelta(minutes=30)

        if time_difference > max_age_threshold:
            # Delete the image from Cloudinary
            result = cloudinary.uploader.destroy(public_id)
            if result.get("result") == "ok":
                print(f"Image with public_id '{public_id}' deleted successfully.")
            else:
                print(f"Failed to delete image with public_id '{public_id}'.")
         
    except Exception as ex:
        print(f"Error deleting image with public_id '{public_id, created_time}': {ex}")

def AnalyzeImage(file, image_file, desc_list):
    print('Analyzing '+ file.filename)

    # Specify features to be retrieved
    features = [VisualFeatureTypes.description,
                VisualFeatureTypes.tags,
                VisualFeatureTypes.categories,
                VisualFeatureTypes.brands,
                VisualFeatureTypes.objects,
                VisualFeatureTypes.adult]
    
    
    # Get image analysis
    #with open(image_file, mode="rb") as image_data:
    analysis = cv_client.analyze_image(image_file, features)

    # Get image description
    for caption in analysis.description.captions:
        print("Description: '{}' (confidence: {:.2f}%)".format(caption.text, caption.confidence * 100))
        desc_list.append("Description: '{}' (confidence: {:.2f}%)".format(caption.text, caption.confidence * 100))

    # Get image tags
    if (len(analysis.tags) > 0):
        print("Tags: ")
        desc_list.append("Tags: \n")
        for tag in analysis.tags:
            print(" -'{}' (confidence: {:.2f}%)".format(tag.name, tag.confidence * 100))
            desc_list.append(" -'{}' (confidence: {:.2f}%)\n".format(tag.name, tag.confidence * 100))


    # Get image categories
    if (len(analysis.categories) > 0):
        print("Categories:")
        desc_list.append("Categories: \n")
        landmarks = []
        for category in analysis.categories:
            # Print the category
            print(" -'{}' (confidence: {:.2f}%)".format(category.name, category.score * 100))
            desc_list.append(" -'{}' (confidence: {:.2f}%)\n".format(category.name, category.score * 100))
            if category.detail:
                # Get landmarks in this category
                if category.detail.landmarks:
                    for landmark in category.detail.landmarks:
                        if landmark not in landmarks:
                            landmarks.append(landmark)

        # If there were landmarks, list them
        if len(landmarks) > 0:
            print("Landmarks:")
            desc_list.append("Landmarks: \n")
            for landmark in landmarks:
                print(" -'{}' (confidence: {:.2f}%)".format(landmark.name, landmark.confidence * 100))
                desc_list.attend(" -'{}' (confidence: {:.2f}%)\n".format(landmark.name, landmark.confidence * 100))
 


    # Get brands in the image
    if (len(analysis.brands) > 0):
        print("Brands: \n")
        desc_list.append("Brands: \n")
        for brand in analysis.brands:
            print(" -'{}' (confidence: {:.2f}%)".format(brand.name, brand.confidence * 100))
            desc_list.append(" -'{}' (confidence: {:.2f}%)\n\n".format(brand.name, brand.confidence * 100))


    # Get objects in the image


    # Get moderation ratings


        

"""
def GetThumbnail(image_file):
    print('Generating thumbnail')

    # Generate a thumbnail
"""

def GenerateCaption(content, desc_list, message):
    #append user prompt to generated description
    desc_list.append(message)

    content = '\n'.join(desc_list)

    message_text = [{"role":"system","content":"You are an AI assistant helping users generate engaging social media captions for images. Given a brief description of the image, and an optional message by the user, provide 3 creative and concise caption that would captivate and inform the audience. Ensure the caption is suitable for sharing on various social platforms. Write in a common way social media users write"},
                    {"role":"user","content":content}]

    #print(desc_list)
    #print(content)
    #print(type(content))
    completion = openai.ChatCompletion.create(
    engine="SocialMedia-ImageCap",
    messages = message_text,
    temperature=0.7,
    max_tokens=800,
    top_p=0.95,
    frequency_penalty=0,
    presence_penalty=0,
    stop=None
    )

    captions = completion.choices[0].message.content
    print(captions)
    return captions

if __name__ == "__main__":
    app.run(debug=False, threading=True)
