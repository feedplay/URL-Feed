import os
import re
import threading
import time
import functools
import concurrent.futures
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from flask import Flask, request, Response, jsonify, make_response
from flask_cors import CORS
from urllib.parse import urlparse
from dotenv import load_dotenv
import json
import uuid
import tldextract  # New import for domain reputation checking

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", os.urandom(24))  # Add a secret key for sessions
# Allow all origins for development, but you can restrict this in production
CORS(app, resources={r"/*": {"origins": "*"}})

# Get Gemini API key from environment
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    print("⚠️ WARNING: GEMINI_API_KEY not found in environment variables.")
    raise ValueError("❌ ERROR: Missing Gemini API Key in .env file!")

# Simple in-memory cache for website content
website_content_cache = {}
# Create a dictionary to store session-specific data
session_data = {}
lock = threading.Lock()  # Prevent concurrency issues

# List of popular/reputable domains that likely have good UX
# This list can be expanded as needed
REPUTABLE_DOMAINS = [
    'google', 'amazon', 'apple', 'microsoft', 'facebook', 'meta', 'twitter', 
    'linkedin', 'github', 'stackoverflow', 'netflix', 'spotify', 'airbnb', 
    'uber', 'shopify', 'stripe', 'slack', 'notion', 'zoom', 'dropbox', 
    'mailchimp', 'hubspot', 'salesforce', 'adobe', 'squarespace', 'wix',
    'wordpress', 'webflow', 'atlassian', 'canva', 'figma', 'asana', 'trello'
]

# Add the GeminiRateLimiter class and rate_limited_gemini_call decorator
import time
from functools import wraps

class GeminiRateLimiter:
    def __init__(self, max_requests=60, per_minute=1):
        """
        Initialize rate limiter for Gemini API
        :param max_requests: Maximum number of requests allowed
        :param per_minute: Time window in minutes
        """
        self.max_requests = max_requests
        self.per_minute = per_minute
        self.request_timestamps = []
        self.last_retry_time = 0
        self.retry_delay = 0

    def wait_if_needed(self):
        """
        Wait if rate limit is exceeded or retry delay is in effect
        """
        current_time = time.time()
        
        # Check if we need to wait due to previous API error
        if current_time < self.last_retry_time + self.retry_delay:
            wait_time = (self.last_retry_time + self.retry_delay) - current_time
            print(f"⏳ Waiting for {wait_time:.2f} seconds due to previous rate limit error")
            time.sleep(wait_time)
        
        # Clean up old request timestamps
        self.request_timestamps = [
            ts for ts in self.request_timestamps 
            if current_time - ts < (self.per_minute * 60)
        ]
        
        # If we've reached max requests, wait
        if len(self.request_timestamps) >= self.max_requests:
            oldest_request = self.request_timestamps[0]
            wait_time = (self.per_minute * 60) - (current_time - oldest_request)
            print(f"⏳ Rate limit reached. Waiting for {wait_time:.2f} seconds")
            time.sleep(wait_time)
        
        # Record this request
        self.request_timestamps.append(current_time)

    def handle_rate_limit_error(self, error):
        """
        Handle rate limit error from Gemini API
        :param error: Exception containing rate limit information
        """
        # Extract retry delay if available
        try:
            retry_delay = error.retry_delay.seconds if hasattr(error, 'retry_delay') else 30
            self.retry_delay = retry_delay
            self.last_retry_time = time.time()
            print(f"🚫 Rate limit error. Retry after {retry_delay} seconds")
        except:
            # Default fallback
            self.retry_delay = 30
            self.last_retry_time = time.time()
            print("🚫 Rate limit error. Using default retry delay")

def rate_limited_gemini_call(func):
    """
    Decorator to add rate limiting to Gemini API calls
    """
    # Shared rate limiter across all calls
    rate_limiter = GeminiRateLimiter()
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Wait if needed before making the call
            rate_limiter.wait_if_needed()
            
            # Make the API call
            return func(*args, **kwargs)
        
        except Exception as e:
            # Check if it's a rate limit error
            if 'quota' in str(e).lower() or '429' in str(e):
                # Handle rate limit error
                rate_limiter.handle_rate_limit_error(e)
                
                # Retry the call after waiting
                rate_limiter.wait_if_needed()
                return func(*args, **kwargs)
            
            # If it's not a rate limit error, re-raise
            raise
    
    return wrapper

# Configure the Gemini API with rate limiting
@rate_limited_gemini_call
def configure_gemini():
    genai.configure(api_key=GEMINI_API_KEY)
    # Use the latest Gemini model with configuration for better structured output
    model = genai.GenerativeModel('gemini-1.5-pro', 
                                 generation_config={
                                     "temperature": 0.1,  # Reduced from 0.2 for more consistent outputs
                                     "top_p": 0.8,
                                     "top_k": 40,
                                     "max_output_tokens": 2048,
                                 })
    return model

# Add caching decorator for expensive operations
def cached_function(expiry_seconds=300):
    """Cache decorator for expensive functions."""
    cache = {}
    lock = threading.Lock()
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            with lock:
                # Check if we have a cached result that hasn't expired
                if key in cache:
                    result, timestamp = cache[key]
                    if time.time() - timestamp < expiry_seconds:
                        print(f"🔄 Cache hit for {func.__name__}")
                        return result
            
            # Run the function and cache the result
            result = func(*args, **kwargs)
            with lock:
                cache[key] = (result, time.time())
            return result
        return wrapper
    return decorator

# Improved helper function to check if a dimension is large with more nuanced thresholds
def is_large_dimension(value, threshold=1200):  # Increased threshold from 1000 to 1200
    """Check if a dimension is considered large, handling percentages and other units."""
    if not value:
        return False
    
    try:
        # If it's a pure number or numeric string
        if str(value).isdigit():
            return int(value) > threshold
        # If it contains '%', it's relative to container
        elif '%' in str(value):
            # Consider percentage dimensions over 80% as potentially large
            percentage = float(str(value).replace('%', ''))
            return percentage > 80
        # Remove 'px' if present and try to convert
        elif 'px' in str(value).lower():
            numeric_part = str(value).lower().replace('px', '')
            return numeric_part.isdigit() and int(numeric_part) > threshold
        # Handle 'em', 'rem', 'vw', 'vh' values
        elif any(unit in str(value).lower() for unit in ['em', 'rem', 'vw', 'vh']):
            # Extract numeric part
            numeric_part = ''.join([c for c in str(value) if c.isdigit() or c == '.'])
            try:
                numeric_value = float(numeric_part)
                # For relative units, use a lower threshold
                if 'em' in str(value) or 'rem' in str(value):
                    return numeric_value > 10  # 10em is quite large
                elif 'vw' in str(value) or 'vh' in str(value):
                    return numeric_value > 50  # 50vw/vh is half the viewport
            except:
                return False
        return False
    except:
        return False

# Check if a website belongs to a reputable domain (new function)
def is_reputable_domain(url):
    """Check if the URL belongs to a reputable domain that likely has good UX practices."""
    try:
        # Extract the domain using tldextract to handle subdomains properly
        extract_result = tldextract.extract(url)
        domain = extract_result.domain.lower()
        
        # Check if the domain name is in our list of reputable domains
        return domain in REPUTABLE_DOMAINS
    except:
        return False

# Extract website content with improved error handling
@cached_function(expiry_seconds=600)
def extract_website_content(url):
    """Extract and analyze website content with caching and better error handling."""
    try:
        if url in website_content_cache:
            print(f"🔄 Website content cache hit for {url}")
            return website_content_cache[url], True
            
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        print(f"🌐 Fetching website content for: {url}")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Basic website data
        title = soup.title.string if soup.title else "No title found"
        
        # Extract text content
        text_content = soup.get_text(separator=' ', strip=True)
        
        # Extract meta descriptions
        meta_description = ""
        meta_tag = soup.find('meta', attrs={'name': 'description'})
        if meta_tag and 'content' in meta_tag.attrs:
            meta_description = meta_tag['content']
        
        # Extract keywords (new)
        keywords = ""
        keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
        if keywords_tag and 'content' in keywords_tag.attrs:
            keywords = keywords_tag['content']
        
        # Extract CTAs, forms, and navigation elements
        ctas = soup.find_all(['button', 'a'], class_=lambda x: x and ('cta' in str(x).lower() or 'btn' in str(x).lower()))
        
        # Additional CTA detection by text content
        additional_ctas = soup.find_all(['button', 'a'], text=lambda x: x and ('sign up' in str(x).lower() or 
                                                                              'get started' in str(x).lower() or 
                                                                              'try now' in str(x).lower() or 
                                                                              'buy now' in str(x).lower() or
                                                                              'subscribe' in str(x).lower() or
                                                                              'download' in str(x).lower() or
                                                                              'join' in str(x).lower() or
                                                                              'start' in str(x).lower()))
        
        # Combine the CTA lists, removing duplicates
        all_ctas = list(set(ctas + additional_ctas))
        
        forms = soup.find_all('form')
        nav_elements = soup.find_all(['nav', 'header', 'menu'])
        
        # Extract social proof elements
        testimonials = soup.find_all(class_=lambda x: x and ('testimonial' in str(x).lower() or 'review' in str(x).lower()))
        
        # Count social proof elements by looking for testimonial-like content
        social_proof_elements = soup.find_all(lambda tag: any(term in str(tag).lower() for term in 
                                                            ['testimonial', 'review', 'stars', 'rating', 'trust', 'customer story']))
        
        # Detect footer elements
        footer_elements = soup.find_all(['footer']) + soup.find_all(class_=lambda x: x and 'footer' in str(x).lower())
        
        # Analyze load speed indicators (script and image count)
        scripts = soup.find_all('script')
        
        # Check for script optimizations (new)
        async_scripts = soup.find_all('script', attrs={'async': True})
        defer_scripts = soup.find_all('script', attrs={'defer': True})
        
        images = soup.find_all('img')
        
        # Check for lazy-loaded images (new)
        lazy_loaded_images = soup.find_all('img', attrs={'loading': 'lazy'})
        
        # Use the improved is_large_dimension function to check image sizes
        large_images = [img for img in images if 
                       (img.get('width') and is_large_dimension(img.get('width'))) or 
                       (img.get('height') and is_large_dimension(img.get('height')))]
        
        # Analyze mobile responsiveness signals
        has_viewport_meta = bool(soup.find('meta', attrs={'name': 'viewport'}))
        responsive_meta = soup.find('meta', attrs={'name': 'viewport'})
        responsive_meta_content = responsive_meta.get('content', '') if responsive_meta else ''
        
        # Count responsive design elements
        media_queries_count = len(re.findall(r'@media', str(soup.find_all('style'))))
        
        # Check for presence of PWA features (new)
        has_manifest = bool(soup.find('link', attrs={'rel': 'manifest'}))
        has_service_worker = bool(re.search(r'serviceWorker', str(soup.find_all('script'))))
        
        # Check for accessibility features (new)
        aria_attributes = len(re.findall(r'aria-[a-z]+', str(soup)))
        
        # Check if domain is reputable
        is_reputable = is_reputable_domain(url)
        
        # Organize data with additional metrics
        website_data = {
            'url': url,
            'title': title,
            'meta_description': meta_description,
            'keywords': keywords,  # New field
            'text_content': text_content[:20000],  # Increased from 10000 to 20000 for better analysis
            'ctas_count': len(all_ctas),
            'forms_count': len(forms),
            'nav_elements_count': len(nav_elements),
            'testimonials_count': len(testimonials) + len(social_proof_elements),
            'footer_elements_count': len(footer_elements),
            'scripts_count': len(scripts),
            'async_scripts_count': len(async_scripts),  # New field
            'defer_scripts_count': len(defer_scripts),  # New field
            'images_count': len(images),
            'lazy_loaded_images_count': len(lazy_loaded_images),  # New field
            'large_images_count': len(large_images),
            'has_responsive_meta': has_viewport_meta,
            'responsive_meta_content': responsive_meta_content,
            'media_queries_count': media_queries_count,
            'has_manifest': has_manifest,  # New field
            'has_service_worker': has_service_worker,  # New field
            'aria_attributes_count': aria_attributes,  # New field
            'is_reputable_domain': is_reputable  # New field to influence scoring
        }
        
        # Store in cache
        website_content_cache[url] = website_data
        
        print(f"✅ Successfully extracted website data for {url}")
        return website_data, True
    except Exception as e:
        error_message = str(e)
        print(f"❌ Error extracting website content: {error_message}")
        
        # Create error data with the URL
        error_data = {'error': error_message, 'url': url}
        return error_data, False

# Parse JSON from response with better error handling
def parse_json_from_response(text):
    """Extract JSON from the AI response with enhanced error handling."""
    if not text or not isinstance(text, str):
        print(f"⚠️ Invalid response text: {type(text)}")
        return create_default_response()
        
    try:
        # First, try to parse the entire response as JSON
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            # If that fails, try to find JSON within markdown code blocks
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
            if json_match:
                json_text = json_match.group(1).strip()
                return json.loads(json_text)
            
            # If no code block, try to find anything that looks like a JSON object
            json_match = re.search(r'(\{[\s\S]*\})', text)
            if json_match:
                return json.loads(json_match.group(1))
        except Exception as e:
            print(f"❌ JSON extraction failed: {str(e)}")
    
    return create_default_response()

def create_default_response():
    """Create a default response structure for fallback scenarios."""
    print(f"⚠️ Using default fallback structure.")
    return {
        "overall_score": 65,
        "health_score": {
            "value": 65,
            "category": "Needs Improvement",
            "description": "Several significant issues that need attention."
        },
        "issues": [
            {
                "category": "Error Processing",
                "description": "We encountered an issue analyzing this website. Please try again.",
                "impact": "High",
                "solution": "Refresh and retry the analysis."
            }
        ]
    }

# Improved health score calculation with more generous scoring for reputable domains
def calculate_health_score(overall_score, is_reputable=False, optimization_indicators=0):
    """
    Calculate health score category and description based on numeric score.
    Adjusts scores for reputable domains and sites with good optimization indicators.
    
    Args:
        overall_score (int): Raw score from 0-100
        is_reputable (bool): Whether the domain is in our reputable list
        optimization_indicators (int): Count of positive optimization indicators
    """
    # Apply bonus points for reputable domains (up to +10)
    if is_reputable:
        bonus = min(10, max(5, overall_score // 10))  # Larger bonus for sites with already decent scores
        adjusted_score = min(100, overall_score + bonus)
        print(f"📈 Adjusting score for reputable domain: {overall_score} → {adjusted_score}")
        overall_score = adjusted_score
    
    # Apply bonus points for optimization indicators (up to +5)
    if optimization_indicators > 0:
        bonus = min(5, optimization_indicators)
        adjusted_score = min(100, overall_score + bonus)
        print(f"📈 Adjusting score for optimization indicators: {overall_score} → {adjusted_score}")
        overall_score = adjusted_score
    
    # Improved thresholds with more nuanced categories
    if overall_score >= 90:
        category = "Excellent"
        description = "Your website is optimized for conversions with only minor improvements needed."
    elif overall_score >= 80:
        category = "Very Good"
        description = "Your website performs well but has some opportunities for improvement."
    elif overall_score >= 70:
        category = "Good"
        description = "Your website has a solid foundation but several areas need attention."
    elif overall_score >= 60:
        category = "Needs Improvement"
        description = "Your website has some issues that may be impacting conversions."
    elif overall_score >= 50:
        category = "Poor"
        description = "Your website has significant conversion issues that need attention."
    else:
        category = "Critical"
        description = "Your website has critical issues that are severely limiting conversions."
    
    return {
        "value": overall_score,
        "category": category,
        "description": description
    }

# Analyze website with rate limiting
@rate_limited_gemini_call
def analyze_website(model, website_data, session_id):
    """Analyze website data using Gemini with enhanced prompt and error handling."""
    # Count optimization indicators
    optimization_indicators = 0
    if website_data.get('async_scripts_count', 0) > 0:
        optimization_indicators += 1
    if website_data.get('defer_scripts_count', 0) > 0:
        optimization_indicators += 1
    if website_data.get('lazy_loaded_images_count', 0) > 0:
        optimization_indicators += 1
    if website_data.get('has_responsive_meta', False):
        optimization_indicators += 1
    if website_data.get('media_queries_count', 0) > 2:
        optimization_indicators += 1
    if website_data.get('has_manifest', False):
        optimization_indicators += 1
    if website_data.get('has_service_worker', False):
        optimization_indicators += 1
    if website_data.get('aria_attributes_count', 0) > 5:
        optimization_indicators += 1
    
    # Improved prompt with more nuanced analysis instructions
    prompt = f"""
    Analyze this website data for UX and conversion rate optimization (CRO) issues:
    
    URL: {website_data['url']}
    Page title: {website_data['title']}
    Meta description: {website_data['meta_description']}
    Keywords: {website_data.get('keywords', 'Not specified')}
    
    Key statistics:
    - CTAs detected: {website_data['ctas_count']}
    - Forms detected: {website_data['forms_count']}
    - Navigation elements: {website_data['nav_elements_count']}
    - Testimonial/social proof elements: {website_data['testimonials_count']}
    - Scripts count: {website_data['scripts_count']}
    - Async scripts: {website_data.get('async_scripts_count', 0)}
    - Defer scripts: {website_data.get('defer_scripts_count', 0)}
    - Images count: {website_data['images_count']}
    - Lazy-loaded images: {website_data.get('lazy_loaded_images_count', 0)}
    - Large images count: {website_data['large_images_count']}
    - Has responsive meta tag: {website_data['has_responsive_meta']}
    - Media queries detected: {website_data['media_queries_count']}
    - Has web app manifest: {website_data.get('has_manifest', False)}
    - Has service worker: {website_data.get('has_service_worker', False)}
    - Accessibility attributes: {website_data.get('aria_attributes_count', 0)}
    
    Page content sample (first part): {website_data['text_content'][:10000]}
    
    Page content sample (second part): {website_data['text_content'][10000:20000]}
    
    Analysis guidelines:
    1. Consider that established/popular websites often use sophisticated techniques
    2. Low element counts might be intentional for minimalist design
    3. High element counts aren't inherently problematic if well-organized
    4. Evaluate page based on UX best practices for its apparent purpose
    5. Consider mobile responsiveness and performance optimization features
    6. Identify issues that genuinely impact conversions, not just technical preferences
    
    Analyze this data for UX and conversion rate optimization issues. Provide your analysis as a structured JSON object with the following format:
    
    {{
      "overall_score": <A number from 0-100 representing overall UX health>,
      "issues": [
        {{
          "category": "<Category name: Call-to-Action, Forms, Navigation, Social Proof, Page Speed, Mobile Responsiveness, or Content>",
          "description": "<Detailed explanation of the issue>",
          "impact": "<High, Medium, or Low>",
          "solution": "<Specific recommendation to fix the issue>"
        }}
      ]
    }}
    
    Identify 5 key issues across different categories that would most impact conversion rates.
    For each issue:
    1. Provide a clear problem description
    2. Explain the expected impact on conversion rates
    3. Give a specific, actionable solution recommendation
    
    Scoring guidance:
    - 90-100: Exceptional websites with minimal issues
    - 80-89: Good websites with a few minor improvements needed
    - 70-79: Decent websites with several areas for improvement
    - 60-69: Websites with significant issues affecting conversions
    - 50-59: Websites with major usability or conversion problems
    - Below 50: Only for websites with critical, pervasive issues
    
    YOU MUST RETURN A VALID JSON OBJECT. DO NOT INCLUDE ANY EXPLANATION TEXT BEFORE OR AFTER THE JSON.
    """
    
    try:
        print(f"🔄 Analyzing website data with Gemini: {website_data['url']}")
        response = model.generate_content(prompt)
        response_text = response.text
        
        # Parse the JSON response
        analysis_data = parse_json_from_response(response_text)
        
        # Add health score data with optimization and reputation adjustments
        if "overall_score" in analysis_data:
            analysis_data["health_score"] = calculate_health_score(
                analysis_data["overall_score"],
                is_reputable=website_data.get('is_reputable_domain', False),
                optimization_indicators=optimization_indicators
            )
        
        # Store in session data
        session_data[session_id]['analysis'] = analysis_data
        
        print(f"✅ Successfully analyzed website: {website_data['url']}")
        return analysis_data, True
    except Exception as e:
        error_message = str(e)
        print(f"❌ Error analyzing website with Gemini: {error_message}")
        
        # Return a default error response
        error_data = create_default_response()
        return error_data, False

# Format the response for the client
def format_response(url, analysis_data):
    """Format the analysis data into a readable text response."""
    try:
        # Check if we have valid analysis data
        if not isinstance(analysis_data, dict) or 'overall_score' not in analysis_data or 'issues' not in analysis_data:
            return f"""WEBSITE ANALYSIS REPORT
URL: {url}

Error: Unable to generate a complete analysis for this website. Please try again.
"""
        
        # Get health score information
        health_score = analysis_data.get('health_score', calculate_health_score(analysis_data['overall_score']))
        
        # Start building the response
        response_text = f"""WEBSITE ANALYSIS REPORT
URL: {url}

OVERALL UX HEALTH SCORE: {analysis_data['overall_score']}/100
HEALTH ASSESSMENT: {health_score['category']} - {health_score['description']}

KEY ISSUES AND RECOMMENDATIONS:
"""
        
        # Add each issue with its description, impact, and solution
        for i, issue in enumerate(analysis_data['issues'], 1):
            response_text += f"""
{i}. {issue.get('category', 'Issue')}
   Problem: {issue.get('description', 'No description available')}
   Impact: {issue.get('impact', 'Unknown')}
   Solution: {issue.get('solution', 'No solution provided')}
"""
        
        return response_text
    except Exception as e:
        print(f"❌ Error formatting response: {str(e)}")
        return f"""WEBSITE ANALYSIS REPORT
URL: {url}

Error: An issue occurred while formatting the analysis results. Please try again.
"""

# Helper function to get or create a session ID
def get_session_id():
    """Get existing session ID from cookie or create a new one"""
    if 'session_id' not in request.cookies:
        return str(uuid.uuid4())
    return request.cookies.get('session_id')

# Cleanup old session data periodically
def cleanup_old_sessions():
    """Delete session data older than 1 hour."""
    try:
        with lock:
            now = time.time()
            sessions_to_remove = []
            for s_id, data in session_data.items():
                if 'timestamp' not in data:
                    data['timestamp'] = now  # Add timestamp for new sessions
                elif data['timestamp'] < now - 3600:
                    sessions_to_remove.append(s_id)
            
            for s_id in sessions_to_remove:
                del session_data[s_id]
                print(f"🧹 Cleaned up old session: {s_id}")
    except Exception as e:
        print(f"❌ Error during session cleanup: {str(e)}")

# Dictionary to store conversation history
chat_histories = {}

# Enhanced endpoint for chat interactions
@app.route('/api/chat', methods=['POST'])
def chat_interaction():
    """Handle chat interactions for CRO-specific conversations"""
    # Get or create session ID
    session_id = get_session_id()
    
    # Get request data
    data = request.get_json(silent=True)
    
    if not data:
        response = make_response(jsonify({"error": "Invalid request format. Expected JSON body."}), 400)
        response.set_cookie('session_id', session_id)
        return response
    
    # Get user message
    user_message = data.get('message')
    if not user_message:
        response = make_response(jsonify({"error": "No message provided"}), 400)
        response.set_cookie('session_id', session_id)
        return response
    
    # Initialize chat history for this session if it doesn't exist
    if session_id not in chat_histories:
        chat_histories[session_id] = []
    
    # Add user message to history
    chat_histories[session_id].append({"role": "user", "content": user_message})
    
    try:
        # Configure Gemini
        model = configure_gemini()
        
        # Check if this is a new conversation
        is_new_conversation = len(chat_histories[session_id]) <= 1
        
        # Create system prompt for CRO-specific chatbot
        system_prompt = """
        You are a Conversion Rate Optimization (CRO) specialist chatbot. Your job is to help users understand and improve their website's conversion rates.
        
        Guidelines:
        1. Be friendly, helpful, and professional.
        2. Only discuss topics related to websites, UX, UI, conversion optimization, and digital marketing.
        3. If the user asks about something unrelated to these topics, politely explain that you can only help with website and CRO-related questions.
        4. If the user says hello or greets you, respond warmly and ask how you can help them with their website or conversion challenges.
        5. Suggest specific actionable advice when possible.
        6. Keep responses concise but informative.
        7. When appropriate, suggest they use the site analyzer tool for comprehensive insights.
        
        Common CRO topics you can discuss:
        - Call-to-Action optimization
        - Form design and conversion
        - Page load speed issues
        - Mobile responsiveness
        - User experience (UX) best practices
        - A/B testing strategies
        - Landing page optimization
        - Checkout optimization
        - Social proof implementation
        - Website copy and messaging
        """
        
        # If this is the first message, handle greetings specially
        if is_new_conversation and any(greeting in user_message.lower() for greeting in ['hi', 'hello', 'hey', 'greetings']):
            response_text = """Hello! I'm your CRO Assistant, here to help optimize your website's conversion rate. 

How can I help you today? I can assist with website analysis, conversion optimization strategies, UX improvements, or answer questions about boosting your conversion rates."""
        else:
            # Build the full conversation context
            conversation_history = "\n".join([f"{'User' if msg['role']=='user' else 'Assistant'}: {msg['content']}" 
                                            for msg in chat_histories[session_id][-5:]])  # Just use last 5 messages
            
            # Create the prompt for the chatbot
            prompt = f"""
            {system_prompt}
            
            Recent conversation:
            {conversation_history}
            
            Respond to the user's most recent message. Remember to only discuss website and CRO-related topics.
            If the user is asking about something unrelated to CRO, websites, UX, or digital marketing, politely redirect them.
            """
            
            # Get response from Gemini
            response = model.generate_content(prompt)
            response_text = response.text
            
            # Check if we need to redirect off-topic conversations
            off_topic_keywords = ["personal", "politics", "medical advice", "legal advice", "investments", 
                                 "dating", "games", "movies", "music", "sports", "weather", "news"]
                                 
            if any(keyword in user_message.lower() for keyword in off_topic_keywords) and not any(cro_term in user_message.lower() for cro_term in ["website", "conversion", "ux", "ui", "page", "user", "customer", "traffic", "bounce", "cro", "optimization"]):
                response_text = """I'm sorry, I'm specialized in website conversion rate optimization and can only help with questions related to improving websites, user experience, or digital marketing strategies. 

Could you ask me something about optimizing your website, improving user experience, or increasing conversion rates?"""
        
        # Add assistant response to history
        chat_histories[session_id].append({"role": "assistant", "content": response_text})
        
        # Return the chat response
        chat_response = {
            "response": response_text
        }
        
        response = make_response(jsonify(chat_response))
        response.set_cookie('session_id', session_id)
        return response
        
    except Exception as e:
        error_message = str(e)
        print(f"❌ Error in chat interaction: {error_message}")
        
        response = make_response(jsonify({
            "error": "Failed to process your question.",
            "response": "I'm having trouble connecting right now. Please try again in a moment."
        }), 500)
        response.set_cookie('session_id', session_id)
        return response

# API endpoint to analyze a URL
@app.route('/api/analyze', methods=['POST'])
def analyze_url():
    # Get or create session ID
    session_id = get_session_id()
    
    # Initialize session data
    if session_id not in session_data:
        with lock:
            session_data[session_id] = {'timestamp': time.time()}
    
    data = request.get_json(silent=True)
    
    # Handle case where request might not be JSON
    if data is None:
        url = request.form.get('url')
    else:
        url = data.get('url')
    
    if not url:
        response = make_response(Response("ERROR: URL is required", mimetype="text/plain; charset=utf-8"), 400)
        response.set_cookie('session_id', session_id)
        return response
    
    if not GEMINI_API_KEY:
        response = make_response(Response("ERROR: Gemini API key not configured on server", mimetype="text/plain; charset=utf-8"), 500)
        response.set_cookie('session_id', session_id)
        return response
    
    # Validate URL
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            response = make_response(Response("ERROR: Invalid URL format", mimetype="text/plain; charset=utf-8"), 400)
            response.set_cookie('session_id', session_id)
            return response
    except:
        response = make_response(Response("ERROR: Invalid URL", mimetype="text/plain; charset=utf-8"), 400)
        response.set_cookie('session_id', session_id)
        return response
    
    # Store URL in session data
    session_data[session_id]['url'] = url
    
    # Configure Gemini
    try:
        model = configure_gemini()
    except Exception as e:
        response = make_response(Response(f"ERROR: Failed to configure Gemini API: {str(e)}", mimetype="text/plain; charset=utf-8"), 500)
        response.set_cookie('session_id', session_id)
        return response
    
    # Extract website content
    website_data, success = extract_website_content(url)
    if not success:
        error_details = website_data.get('error', 'Unknown error')
        response = make_response(Response(f"ERROR: Failed to extract website content. Details: {error_details}", 
                        mimetype="text/plain; charset=utf-8"), 500)
        response.set_cookie('session_id', session_id)
        return response
    
    # Store website data in session
    session_data[session_id]['website_data'] = website_data
    
    # Analyze website
    analysis_data, success = analyze_website(model, website_data, session_id)
    if not success:
        response = make_response(Response(f"ERROR: Failed to analyze website. Please try again later.", 
                        mimetype="text/plain; charset=utf-8"), 500)
        response.set_cookie('session_id', session_id)
        return response
    
    # Format the response
    response_text = format_response(url, analysis_data)
    
    # Return analysis results as plain text with UTF-8 encoding
    response = make_response(Response(response_text, mimetype="text/plain; charset=utf-8"))
    response.set_cookie('session_id', session_id)
    return response

# API endpoint for JSON output
@app.route('/api/analyze/json', methods=['POST'])
def analyze_url_json():
    # Get or create session ID
    session_id = get_session_id()
    
    # Initialize session data
    if session_id not in session_data:
        with lock:
            session_data[session_id] = {'timestamp': time.time()}
    
    data = request.get_json(silent=True)
    
    # Handle case where request might not be JSON
    if data is None:
        url = request.form.get('url')
    else:
        url = data.get('url')
    
    if not url:
        response = make_response(jsonify({"error": "URL is required"}), 400)
        response.set_cookie('session_id', session_id)
        return response
    
    if not GEMINI_API_KEY:
        response = make_response(jsonify({"error": "Gemini API key not configured on server"}), 500)
        response.set_cookie('session_id', session_id)
        return response
    
    # Validate URL
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            response = make_response(jsonify({"error": "Invalid URL format"}), 400)
            response.set_cookie('session_id', session_id)
            return response
    except:
        response = make_response(jsonify({"error": "Invalid URL"}), 400)
        response.set_cookie('session_id', session_id)
        return response
    
    # Store URL in session data
    session_data[session_id]['url'] = url
    
    # Configure Gemini
    try:
        model = configure_gemini()
    except Exception as e:
        response = make_response(jsonify({"error": f"Failed to configure Gemini API: {str(e)}"}), 500)
        response.set_cookie('session_id', session_id)
        return response
    
    # Extract website content
    website_data, success = extract_website_content(url)
    if not success:
        error_details = website_data.get('error', 'Unknown error')
        response = make_response(jsonify({"error": f"Failed to extract website content: {error_details}"}), 500)
        response.set_cookie('session_id', session_id)
        return response
    
    # Store website data in session
    session_data[session_id]['website_data'] = website_data
    
    # Analyze website
    analysis_data, success = analyze_website(model, website_data, session_id)
    if not success:
        response = make_response(jsonify({"error": "Failed to analyze website. Please try again later."}), 500)
        response.set_cookie('session_id', session_id)
        return response
    
    # Add URL to the response
    analysis_data['url'] = url
    
    # Return JSON response
    response = make_response(jsonify(analysis_data))
    response.set_cookie('session_id', session_id)
    return response

# Status endpoint to check if API is running
@app.route('/api/status', methods=['GET'])
def status():
    # Clean up old sessions
    cleanup_old_sessions()
    
    status_text = "CRO Optimizer API Status: Running\nGemini API Configured: " + str(bool(GEMINI_API_KEY))
    response = make_response(Response(status_text, mimetype="text/plain; charset=utf-8"))
    
    # Get or create session ID
    session_id = get_session_id()
    response.set_cookie('session_id', session_id)
    
    return response

# Homepage with basic information
@app.route('/')
def home():
    # Clean up old sessions
    cleanup_old_sessions()
    
    # Get or create session ID
    session_id = get_session_id()
    
    # Initialize session data if needed
    if session_id not in session_data:
        with lock:
            session_data[session_id] = {'timestamp': time.time()}
    
    html_response = """
    <html>
    <head>
        <title>CRO Optimizer API</title>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }
            h1 { color: #4A90E2; }
            .status { padding: 10px; background-color: #E3F2FD; border-radius: 4px; margin-bottom: 20px; }
            code { background: #f4f4f4; padding: 2px 5px; border-radius: 3px; }
            pre { background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }
            .endpoint { margin-bottom: 30px; }
        </style>
    </head>
    <body>
        <h1>CRO Optimizer API</h1>
        <div class="status">✅ CRO Optimizer API with Gemini is running!</div>
        
        <p>This API analyzes websites and provides feedback on:</p>
        <ul>
            <li>Call-to-Action Visibility</li>
            <li>Form Field Optimization</li>
            <li>Mobile Navigation Issues</li>
            <li>Social Proof Placement</li>
            <li>Page Speed Optimization</li>
            <li>Content Clarity</li>
        </ul>
        
        <div class="endpoint">
            <h2>Text Response Endpoint</h2>
            <p>Send a POST request to <code>/api/analyze</code> with a URL to get a text analysis report.</p>
            <pre>curl -X POST -H "Content-Type: application/json" -d '{"url":"https://example.com"}' http://localhost:5000/api/analyze</pre>
        </div>
        
        <div class="endpoint">
            <h2>JSON Response Endpoint</h2>
            <p>Send a POST request to <code>/api/analyze/json</code> for a structured JSON response.</p>
            <pre>curl -X POST -H "Content-Type: application/json" -d '{"url":"https://example.com"}' http://localhost:5000/api/analyze/json</pre>
        </div>
        
        <div class="endpoint">
            <h2>Status Check</h2>
            <p>Send a GET request to <code>/api/status</code> to check if the API is running.</p>
            <pre>curl http://localhost:5000/api/status</pre>
        </div>
    </body>
    </html>
    """
    
    response = make_response(html_response)
    response.set_cookie('session_id', session_id)
    return response

# Serve static files for the React app in production
@app.route('/<path:path>')
def serve(path):
    # In production, this would serve the built React app
    # For development, this route isn't needed (React dev server handles it)
    return Response("CRO Optimizer API is running. Frontend should be served separately in development.", 
                   mimetype="text/plain; charset=utf-8")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting CRO Optimizer API on port {port}...")
    try:
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        print(f"🔥 Error starting Flask: {e}")
