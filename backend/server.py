from fastapi import FastAPI, APIRouter, HTTPException, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import httpx
from bs4 import BeautifulSoup
import re
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import json
from bson import ObjectId

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Current Affairs API", description="Educational platform for UPSC and state-level exam preparation")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Indian States and Districts mapping
INDIAN_STATES_DISTRICTS = {
    "Andhra Pradesh": ["Visakhapatnam", "Vijayawada", "Guntur", "Nellore", "Kurnool"],
    "Arunachal Pradesh": ["Itanagar", "Naharlagun", "Pasighat", "Bomdila", "Tawang"],
    "Assam": ["Guwahati", "Dibrugarh", "Silchar", "Jorhat", "Nagaon"],
    "Bihar": ["Patna", "Gaya", "Bhagalpur", "Muzaffarpur", "Darbhanga"],
    "Chhattisgarh": ["Raipur", "Bhilai", "Korba", "Bilaspur", "Durg"],
    "Goa": ["Panaji", "Margao", "Vasco da Gama", "Mapusa", "Ponda"],
    "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Bhavnagar"],
    "Haryana": ["Gurugram", "Faridabad", "Panipat", "Ambala", "Karnal"],
    "Himachal Pradesh": ["Shimla", "Manali", "Dharamshala", "Solan", "Mandi"],
    "Jharkhand": ["Ranchi", "Jamshedpur", "Dhanbad", "Bokaro", "Deoghar"],
    "Karnataka": ["Bangalore", "Mysore", "Hubli", "Mangalore", "Belgaum"],
    "Kerala": ["Kochi", "Thiruvananthapuram", "Kozhikode", "Thrissur", "Kollam"],
    "Madhya Pradesh": ["Bhopal", "Indore", "Gwalior", "Jabalpur", "Ujjain"],
    "Maharashtra": ["Mumbai", "Pune", "Nagpur", "Nashik", "Aurangabad"],
    "Manipur": ["Imphal", "Thoubal", "Bishnupur", "Churachandpur", "Kakching"],
    "Meghalaya": ["Shillong", "Tura", "Jowai", "Nongpoh", "Baghmara"],
    "Mizoram": ["Aizawl", "Lunglei", "Serchhip", "Champhai", "Kolasib"],
    "Nagaland": ["Kohima", "Dimapur", "Mokokchung", "Tuensang", "Wokha"],
    "Odisha": ["Bhubaneswar", "Cuttack", "Rourkela", "Berhampur", "Sambalpur"],
    "Punjab": ["Chandigarh", "Ludhiana", "Amritsar", "Jalandhar", "Patiala"],
    "Rajasthan": ["Jaipur", "Jodhpur", "Kota", "Bikaner", "Udaipur"],
    "Sikkim": ["Gangtok", "Namchi", "Gyalshing", "Mangan", "Soreng"],
    "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem"],
    "Telangana": ["Hyderabad", "Warangal", "Nizamabad", "Khammam", "Karimnagar"],
    "Tripura": ["Agartala", "Dharmanagar", "Udaipur", "Kailashahar", "Belonia"],
    "Uttar Pradesh": ["Lucknow", "Kanpur", "Ghaziabad", "Agra", "Varanasi"],
    "Uttarakhand": ["Dehradun", "Haridwar", "Roorkee", "Haldwani", "Rishikesh"],
    "West Bengal": ["Kolkata", "Howrah", "Durgapur", "Asansol", "Siliguri"],
    "Jammu and Kashmir": ["Srinagar", "Jammu", "Ramban", "Anantnag", "Baramulla"],
    "Ladakh": ["Leh", "Kargil", "Nubra", "Changthang", "Zanskar"],
    "Delhi": ["New Delhi", "North Delhi", "South Delhi", "East Delhi", "West Delhi"],
    "Puducherry": ["Puducherry", "Karaikal", "Mahe", "Yanam", "Ozhukarai"]
}

# News Sources Configuration
NEWS_SOURCES = {
    "indian": [
        {"name": "NDTV", "url": "https://www.ndtv.com/latest", "selector": "h2.story-title"},
        {"name": "The Hindu", "url": "https://www.thehindu.com/news/", "selector": ".story-card-news h3"},
        {"name": "Times of India", "url": "https://timesofindia.indiatimes.com/", "selector": ".news_Itm h2"},
        {"name": "Indian Express", "url": "https://indianexpress.com/", "selector": ".story-details h2"}
    ],
    "global": [
        {"name": "BBC", "url": "https://www.bbc.com/news", "selector": "h3[data-testid='card-headline']"},
        {"name": "CNN", "url": "https://edition.cnn.com/", "selector": ".container__headline"},
        {"name": "Reuters", "url": "https://www.reuters.com/world/", "selector": "[data-testid='Heading']"}
    ]
}

# Define Models
class NewsItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    summary: Optional[str] = None
    content: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    category: Optional[str] = None
    source: str
    url: Optional[str] = None
    published_at: datetime = Field(default_factory=datetime.utcnow)
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    is_global: bool = False

class NewsSearchQuery(BaseModel):
    q: str
    limit: int = 20
    state: Optional[str] = None
    category: Optional[str] = None

# In-memory cache
news_cache = {
    "global": [],
    "india": [],
    "last_updated": datetime.utcnow()
}

# Initialize scheduler
scheduler = BackgroundScheduler()

def serialize_doc(doc):
    """Convert MongoDB document to JSON serializable format"""
    if isinstance(doc, dict):
        return {key: serialize_doc(value) for key, value in doc.items()}
    elif isinstance(doc, list):
        return [serialize_doc(item) for item in doc]
    elif isinstance(doc, ObjectId):
        return str(doc)
    elif isinstance(doc, datetime):
        return doc.isoformat()
    else:
        return doc

def extract_state_district(text: str) -> tuple[Optional[str], Optional[str]]:
    """Extract state and district from news text using keyword matching"""
    text_lower = text.lower()
    
    for state, districts in INDIAN_STATES_DISTRICTS.items():
        state_lower = state.lower()
        if state_lower in text_lower:
            # Check for districts in the same state
            for district in districts:
                if district.lower() in text_lower:
                    return state, district
            return state, None
    
    # Check for districts without state match
    for state, districts in INDIAN_STATES_DISTRICTS.items():
        for district in districts:
            if district.lower() in text_lower:
                return state, district
    
    return None, None

def categorize_news(text: str) -> str:
    """Categorize news based on keywords"""
    text_lower = text.lower()
    
    categories = {
        "politics": ["election", "government", "minister", "parliament", "policy", "politics", "political"],
        "economy": ["economy", "economic", "gdp", "inflation", "market", "finance", "budget", "tax"],
        "education": ["education", "exam", "upsc", "neet", "jee", "school", "college", "university", "student"],
        "science": ["science", "research", "technology", "innovation", "discovery", "study", "scientist"],
        "environment": ["environment", "climate", "pollution", "green", "renewable", "carbon", "ecosystem"],
        "sports": ["sports", "cricket", "football", "olympics", "match", "tournament", "athlete"],
        "health": ["health", "medical", "hospital", "doctor", "medicine", "disease", "treatment"],
        "defense": ["army", "navy", "air force", "defense", "military", "security", "border"]
    }
    
    for category, keywords in categories.items():
        if any(keyword in text_lower for keyword in keywords):
            return category
    
    return "general"

async def scrape_news_from_source(source: dict, is_global: bool = False) -> List[NewsItem]:
    """Scrape news from a specific source"""
    news_items = []
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = await client.get(source["url"], headers=headers)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                headlines = soup.select(source["selector"])[:10]  # Limit to 10 articles per source
                
                for headline in headlines:
                    title = headline.get_text(strip=True)
                    if title and len(title) > 10:  # Filter out very short titles
                        # Get the link if available
                        link_elem = headline.find('a') or headline.find_parent('a')
                        url = None
                        if link_elem:
                            href = link_elem.get('href')
                            if href:
                                if href.startswith('http'):
                                    url = href
                                else:
                                    base_url = source["url"].split('/')[0] + '//' + source["url"].split('/')[2]
                                    url = base_url + href
                        
                        # Extract state and district for Indian news
                        state, district = None, None
                        if not is_global:
                            state, district = extract_state_district(title)
                        
                        # Categorize news
                        category = categorize_news(title)
                        
                        news_item = NewsItem(
                            title=title,
                            summary=title[:200] + "..." if len(title) > 200 else title,
                            state=state,
                            district=district,
                            category=category,
                            source=source["name"],
                            url=url,
                            is_global=is_global
                        )
                        # Convert to dict and serialize datetime objects
                        item_dict = news_item.dict()
                        item_dict['published_at'] = item_dict['published_at'].isoformat()
                        item_dict['scraped_at'] = item_dict['scraped_at'].isoformat()
                        news_items.append(item_dict)
    
    except Exception as e:
        logger.error(f"Error scraping from {source['name']}: {str(e)}")
    
    return news_items

async def update_news_cache():
    """Update the news cache by scraping from all sources"""
    try:
        logger.info("Starting news cache update...")
        
        # Clear existing cache
        news_cache["global"] = []
        news_cache["india"] = []
        
        # Scrape global news
        for source in NEWS_SOURCES["global"]:
            global_news = await scrape_news_from_source(source, is_global=True)
            news_cache["global"].extend(global_news)
        
        # Scrape Indian news
        for source in NEWS_SOURCES["indian"]:
            indian_news = await scrape_news_from_source(source, is_global=False)
            news_cache["india"].extend(indian_news)
        
        # Store in database
        if news_cache["global"]:
            await db.news.delete_many({"is_global": True})
            # Clean items before storing (remove any _id fields)
            clean_global = []
            for item in news_cache["global"]:
                clean_item = {k: v for k, v in item.items() if k != '_id'}
                clean_global.append(clean_item)
            await db.news.insert_many(clean_global)
        
        if news_cache["india"]:
            await db.news.delete_many({"is_global": False})
            # Clean items before storing (remove any _id fields)
            clean_india = []
            for item in news_cache["india"]:
                clean_item = {k: v for k, v in item.items() if k != '_id'}
                clean_india.append(clean_item)
            await db.news.insert_many(clean_india)
        
        news_cache["last_updated"] = datetime.utcnow()
        logger.info(f"News cache updated successfully. Global: {len(news_cache['global'])}, India: {len(news_cache['india'])}")
        
    except Exception as e:
        logger.error(f"Error updating news cache: {str(e)}")

# API Routes
@api_router.get("/")
async def root():
    return {
        "message": "Current Affairs API for Educational Platform",
        "version": "1.0.0",
        "endpoints": [
            "/api/news/global",
            "/api/news/india", 
            "/api/news/state/{state_name}",
            "/api/news/search"
        ]
    }

@api_router.get("/debug/sample")
async def debug_sample():
    """Debug endpoint to check one sample item"""
    try:
        if news_cache["global"]:
            sample = news_cache["global"][0]
            return {"sample": str(sample), "type": str(type(sample))}
        else:
            return {"message": "No global news in cache"}
    except Exception as e:
        return {"error": str(e)}

@api_router.get("/news/global")
async def get_global_news(limit: int = Query(20, ge=1, le=100)):
    """Get latest global news"""
    try:
        # Return from cache - clean any ObjectId fields
        cached_news = []
        for item in news_cache["global"][:limit]:
            clean_item = {k: v for k, v in item.items() if k != '_id'}
            cached_news.append(clean_item)
            
        return {
            "news": cached_news, 
            "total": len(cached_news), 
            "source": "cache",
            "status": "success"
        }
    
    except Exception as e:
        logger.error(f"Error fetching global news: {str(e)}")
        return {
            "news": [], 
            "total": 0, 
            "error": str(e),
            "status": "error"
        }

@api_router.get("/news/india")
async def get_india_news(limit: int = Query(20, ge=1, le=100)):
    """Get latest India news"""
    try:
        # If cache is old, try to get from database
        if datetime.utcnow() - news_cache["last_updated"] > timedelta(minutes=30):
            db_news = await db.news.find({"is_global": False}).sort("published_at", -1).limit(limit).to_list(limit)
            if db_news:
                serialized_news = [serialize_doc(doc) for doc in db_news]
                return {"news": serialized_news, "total": len(serialized_news), "source": "database"}
        
        # Return from cache
        cached_news = news_cache["india"][:limit]
        return {"news": cached_news, "total": len(cached_news), "source": "cache"}
    
    except Exception as e:
        logger.error(f"Error fetching India news: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching India news")

@api_router.get("/news/state/{state_name}")
async def get_state_news(state_name: str, limit: int = Query(20, ge=1, le=100)):
    """Get news filtered by Indian state"""
    try:
        # Format state name
        state_name = state_name.replace("-", " ").title()
        
        if state_name not in INDIAN_STATES_DISTRICTS:
            raise HTTPException(status_code=404, detail=f"State '{state_name}' not found")
        
        # Search in cache first
        state_news = [
            item for item in news_cache["india"] 
            if item.get("state") == state_name
        ][:limit]
        
        if not state_news:
            # Search in database
            state_news_db = await db.news.find({
                "is_global": False,
                "state": state_name
            }).sort("published_at", -1).limit(limit).to_list(limit)
            state_news = [serialize_doc(doc) for doc in state_news_db]
        
        return {
            "news": state_news, 
            "total": len(state_news), 
            "state": state_name,
            "districts": INDIAN_STATES_DISTRICTS[state_name]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching state news: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching state news")

@api_router.get("/news/search")
async def search_news(
    q: str = Query(..., description="Search keyword"),
    limit: int = Query(20, ge=1, le=100),
    state: Optional[str] = Query(None, description="Filter by state"),
    category: Optional[str] = Query(None, description="Filter by category")
):
    """Search news by keywords with optional filters"""
    try:
        # Build search query
        search_filter = {}
        
        if state:
            state = state.replace("-", " ").title()
            search_filter["state"] = state
        
        if category:
            search_filter["category"] = category.lower()
        
        # Search in database using text search
        db_query = {
            "$text": {"$search": q},
            **search_filter
        }
        
        # Try to create text index if it doesn't exist
        try:
            await db.news.create_index([("title", "text"), ("summary", "text")])
        except:
            pass  # Index might already exist
        
        search_results = await db.news.find(db_query).sort("published_at", -1).limit(limit).to_list(limit)
        search_results = [serialize_doc(doc) for doc in search_results]
        
        # If no results from database, search in cache
        if not search_results:
            all_cached_news = news_cache["global"] + news_cache["india"]
            search_results = []
            
            q_lower = q.lower()
            for item in all_cached_news:
                if (q_lower in item.get("title", "").lower() or 
                    q_lower in item.get("summary", "").lower()):
                    
                    # Apply filters
                    if state and item.get("state") != state:
                        continue
                    if category and item.get("category") != category.lower():
                        continue
                    
                    search_results.append(item)
                    
                    if len(search_results) >= limit:
                        break
        
        return {
            "news": search_results,
            "total": len(search_results),
            "query": q,
            "filters": {"state": state, "category": category}
        }
    
    except Exception as e:
        logger.error(f"Error searching news: {str(e)}")
        raise HTTPException(status_code=500, detail="Error searching news")

@api_router.get("/states")
async def get_states():
    """Get list of all Indian states and their districts"""
    return {"states": INDIAN_STATES_DISTRICTS}

@api_router.post("/news/refresh")
async def refresh_news():
    """Manually refresh news cache"""
    try:
        await update_news_cache()
        return {
            "message": "News cache refreshed successfully",
            "global_count": len(news_cache["global"]),
            "india_count": len(news_cache["india"]),
            "last_updated": news_cache["last_updated"]
        }
    except Exception as e:
        logger.error(f"Error refreshing news: {str(e)}")
        raise HTTPException(status_code=500, detail="Error refreshing news")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    """Initialize the application"""
    logger.info("Starting Current Affairs API...")
    
    # Update news cache on startup
    await update_news_cache()
    
    # Schedule news updates every 30 minutes
    scheduler.add_job(
        func=lambda: asyncio.create_task(update_news_cache()),
        trigger=IntervalTrigger(minutes=30),
        id='news_update_job',
        name='Update news cache every 30 minutes',
        replace_existing=True
    )
    scheduler.start()
    logger.info("News update scheduler started")

@app.on_event("shutdown")
async def shutdown_db_client():
    """Cleanup on shutdown"""
    scheduler.shutdown()
    client.close()
    logger.info("Application shutdown complete")