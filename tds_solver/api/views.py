from django.shortcuts import render

# Create your views here.
# api/views.py
import os
import zipfile
import pandas as pd
import csv
import json
import tempfile
import openai
from pathlib import Path
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

class TDSSolverView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request, format=None):
        question = request.data.get('question', '')
        file_obj = request.data.get('file', None)
        
        # Process file if provided
        file_content = None
        if file_obj:
            file_path = self._save_temp_file(file_obj)
            file_content = self._process_file(file_path)
            
        # Generate answer using LLM
        answer = self._generate_answer(question, file_content)
        
        return Response({"answer": answer})
    
    def _save_temp_file(self, file_obj):
        """Save uploaded file to temporary location"""
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, file_obj.name)
        
        with open(file_path, 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)
                
        return file_path
    
    def _process_file(self, file_path):
        """Process file based on extension"""
        if file_path.endswith('.zip'):
            return self._process_zip_file(file_path)
        elif file_path.endswith('.csv'):
            return self._process_csv_file(file_path)
        # Add more file handlers as needed
        return None
    
    def _process_zip_file(self, zip_path):
        """Extract zip file and process its contents"""
        extract_dir = tempfile.mkdtemp()
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
            
        # Process the extracted files
        results = {}
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                file_path = os.path.join(root, file)
                if file.endswith('.csv'):
                    results[file] = self._process_csv_file(file_path)
                # Add more file type processors as needed
                
        return results
    
    def _process_csv_file(self, csv_path):
        """Process CSV file and return its contents"""
        try:
            df = pd.read_csv(csv_path)
            return df.to_dict(orient='records')
        except Exception as e:
            return f"Error processing CSV: {str(e)}"
    
    def _generate_answer(self, question, file_content=None):
        """Generate answer using LLM"""
        # Prepare context
        prompt = f"You are an assistant that helps with data science assignments. Answer the following question:\n\n{question}"
        
        if file_content:
            prompt += f"\n\nFile content: {json.dumps(file_content)}"
            
        try:
            # Call OpenAI API
            openai.api_key = settings.OPENAI_API_KEY
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant for data science assignments. Provide direct answers."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for more focused answers
                max_tokens=500
            )
            
            # Extract the answer
            answer = response.choices[0].message['content'].strip()
            
            # Clean up the answer to ensure it's just the value
            # Remove explanations or any text that isn't the direct answer
            return self._extract_direct_answer(answer, question)
            
        except Exception as e:
            return f"Error generating answer: {str(e)}"
    
    def _extract_direct_answer(self, answer, question):
        """Extract just the direct answer value from the LLM response"""
        lines = answer.split('\n')
        for line in lines:
            if "answer" in line.lower() and ":" in line:
                return line.split(":", 1)[1].strip()
        
        # If no clear answer format, return the shortest non-empty line
        non_empty_lines = [line.strip() for line in lines if line.strip()]
        if non_empty_lines:
            return min(non_empty_lines, key=len)
            
        return answer  # Fall back to the full answer if extraction fails