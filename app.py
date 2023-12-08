from dotenv import load_dotenv
import os
from array import array
from PIL import Image, ImageDraw
import time
from matplotlib import pyplot as plt
import numpy as np
from flask import Flask, request, jsonify

import openai

app = Flask(__name__)

openai.api_type = "azure"
openai.api_base = "https://generativecaption.openai.azure.com/"
openai.api_version = "2023-07-01-preview"

# import namespaces
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
from msrest.authentication import CognitiveServicesCredentials


@app.route('/analyze', methods=["POST"])
def main():
    global cv_client

    try:
        # Get Configuration Settings
        load_dotenv()
        cog_endpoint = os.environ.get('COG_SERVICE_ENDPOINT') #os.getenv
        cog_key = os.environ.get('COG_SERVICE_KEY')
        openai.api_key = os.environ.get("OPENAI_API_KEY")

        # Get image
        image_file = request.files.get("image")
        if image_file:

            #image_file = 'person.jpg'

            #enter = request.get_json()
            #message = (enter['prompt'])
            message = request.form.get('prompt')
            #message = input("enter a prompt (optional): ")

            # Authenticate Azure AI Vision client
            credential = CognitiveServicesCredentials(cog_key) 
            cv_client = ComputerVisionClient(cog_endpoint, credential)
            content = 'content' #file content


            # Analyze image
            AnalyzeImage(image_file, content)

            #Generate Caption
            caption = GenerateCaption(content, message)

            # Generate thumbnail
            #GetThumbnail(image_file)

            response = {"response": caption}
            return jsonify(response), 200
        else:
            return jsonify({"error": "No image file provided!"}), 400


    except Exception as ex:
        print(ex)
        return jsonify({"error": str(ex)}), 500

def AnalyzeImage(image_file, content):
    #print('Analyzing', image_file.filename())

    # Specify features to be retrieved
    features = [VisualFeatureTypes.description,
                VisualFeatureTypes.tags,
                VisualFeatureTypes.categories,
                VisualFeatureTypes.brands,
                VisualFeatureTypes.objects,
                VisualFeatureTypes.adult]
    
    
    # Get image analysis
    with open(image_file.filename, mode="rb") as image_data:
        analysis = cv_client.analyze_image_in_stream(image_data , features)

    # Get image description
    with open(content, mode="w") as file:
        for caption in analysis.description.captions:
            print("Description: '{}' (confidence: {:.2f}%)".format(caption.text, caption.confidence * 100))
            file.write("Description: '{}' (confidence: {:.2f}%)\n".format(caption.text, caption.confidence * 100))

    # Get image tags
    with open(content, mode="a") as file:
        if (len(analysis.tags) > 0):
            print("Tags: ")
            file.write("Tags: \n")
            for tag in analysis.tags:
                print(" -'{}' (confidence: {:.2f}%)".format(tag.name, tag.confidence * 100))
                file.write(" -'{}' (confidence: {:.2f}%)\n".format(tag.name, tag.confidence * 100))


    # Get image categories
    with open(content, mode="a") as file:
        if (len(analysis.categories) > 0):
            print("Categories:")
            file.write("Categories: \n")
            landmarks = []
            for category in analysis.categories:
                # Print the category
                print(" -'{}' (confidence: {:.2f}%)".format(category.name, category.score * 100))
                file.write(" -'{}' (confidence: {:.2f}%)\n".format(category.name, category.score * 100))
                if category.detail:
                    # Get landmarks in this category
                    if category.detail.landmarks:
                        for landmark in category.detail.landmarks:
                            if landmark not in landmarks:
                                landmarks.append(landmark)

            # If there were landmarks, list them
            if len(landmarks) > 0:
                print("Landmarks:")
                file.write("Landmarks: \n")
                for landmark in landmarks:
                    print(" -'{}' (confidence: {:.2f}%)".format(landmark.name, landmark.confidence * 100))
                    file.write(" -'{}' (confidence: {:.2f}%)\n".format(landmark.name, landmark.confidence * 100))
 


    # Get brands in the image
    with open(content, mode="a") as file:
        if (len(analysis.brands) > 0):
            print("Brands: \n")
            for brand in analysis.brands:
                print(" -'{}' (confidence: {:.2f}%)".format(brand.name, brand.confidence * 100))
                file.write(" -'{}' (confidence: {:.2f}%)\n\n".format(brand.name, brand.confidence * 100))


    # Get objects in the image


    # Get moderation ratings


        

"""
def GetThumbnail(image_file):
    print('Generating thumbnail')

    # Generate a thumbnail
"""

def GenerateCaption(content, message):
    with open(content, mode="a") as file:
        file.write(message)

    with open(content, mode="r") as file:
        content = file.read()
        message_text = [{"role":"system","content":"You are an AI assistant helping users generate engaging social media captions for images. Given a brief description of the image, and an optional message by the user, provide 3 creative and concise caption that would captivate and inform the audience. Ensure the caption is suitable for sharing on various social platforms. Write in a common way social media users write"},
                    {"role":"user","content":content}]

    #print(content)
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
    app.run(debug=True)
