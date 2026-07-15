import csv
import requests
import time
import re
import json
from urllib.parse import quote
USER = "userA"  # Change this to your username
def clean_series_title(title):
    return re.sub(r"\s*\(.*?\)", "", title).strip()

def extract_series(title):
    match = re.search(r"\((.*?)\)", title)
    return match.group(1).strip() if match else None

def clean_isbn(isbn):
    if not isbn:
        return ""
    return isbn.replace("=", "").replace('"', "").replace("'", "").strip()

def normalize(text):
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return text.strip()

# -------- Genre/Mood Classification Functions --------

def classify_genre_and_mood(tags, title, author, description):
    """Classify genres and moods from available data"""
    genres = set()
    moods = set()
    
    # Common genre keywords
    genre_keywords = {
        'fantasy': ['fantasy', 'magic', 'dragon', 'sword', 'wizard', 'sorcerer', 'mythical', 'fairy tale', 'folklore'],
        'science fiction': ['sci-fi', 'science fiction', 'space', 'alien', 'dystopian', 'futuristic', 'cyberpunk', 'robot', 'ai'],
        'mystery': ['mystery', 'detective', 'crime', 'suspense', 'thriller', 'whodunit', 'investigation', 'murder'],
        'romance': ['romance', 'love', 'relationship', 'couple', 'dating', 'romantic'],
        'historical fiction': ['historical', 'period', 'vintage', '19th century', 'victorian', 'medieval'],
        'contemporary': ['contemporary', 'modern', 'current', 'present day'],
        'literary fiction': ['literary', 'literature', 'classic', 'award-winning', 'booker'],
        'horror': ['horror', 'scary', 'haunting', 'macabre', 'gothic', 'paranormal'],
        'young adult': ['ya', 'young adult', 'teen', 'coming of age'],
        'new adult': ['new adult', 'na'],
        'adventure': ['adventure', 'quest', 'journey', 'exploration', 'survival'],
        'comedy': ['comedy', 'humor', 'funny', 'hilarious', 'laugh'],
        'drama': ['drama', 'emotional', 'heartbreaking', 'tragic', 'melancholy'],
        'thriller': ['thriller', 'suspense', 'psychological', 'twisted', 'edge of your seat'],
        'non-fiction': ['non-fiction', 'biography', 'memoir', 'history', 'science', 'philosophy'],
        'magical realism': ['magical realism', 'magical', 'realism', 'surreal'],
        'romantasy': ['romantasy', 'fantasy romance'],
        'cozy': ['cozy', 'comforting', 'gentle', 'heartwarming'],
        'dark': ['dark', 'grim', 'bleak', 'gritty']
    }
    
    # Common mood keywords
    mood_keywords = {
        'dark': ['dark', 'grim', 'bleak', 'macabre', 'gothic'],
        'emotional': ['emotional', 'heartbreaking', 'poignant', 'tearjerker', 'moving'],
        'hopeful': ['hopeful', 'inspiring', 'uplifting', 'optimistic'],
        'suspenseful': ['suspenseful', 'tension', 'edge of your seat', 'thrilling'],
        'humorous': ['humorous', 'funny', 'witty', 'comedic'],
        'thought-provoking': ['thought-provoking', 'philosophical', 'deep', 'intellectual'],
        'romantic': ['romantic', 'swoon', 'heartfelt', 'love'],
        'adventurous': ['adventurous', 'exciting', 'action-packed'],
        'mysterious': ['mysterious', 'enigmatic', 'puzzling'],
        'heartwarming': ['heartwarming', 'wholesome', 'feel-good', 'comforting'],
        'challenging': ['challenging', 'controversial', 'difficult', 'heavy'],
        'nostalgic': ['nostalgic', 'bittersweet', 'sentimental']
    }
    
    # Combine all text for analysis
    text_to_analyze = " ".join(tags + [title, author, description]).lower()
    
    # Classify genres
    for genre, keywords in genre_keywords.items():
        if any(keyword in text_to_analyze for keyword in keywords):
            genres.add(genre)
    
    # Classify moods
    for mood, keywords in mood_keywords.items():
        if any(keyword in text_to_analyze for keyword in keywords):
            moods.add(mood)
    
    # Clean up - remove generic or overlapping genres
    if 'fantasy' in genres and 'magical realism' in genres:
        genres.remove('magical realism')
    
    return list(genres), list(moods)

def extract_enhanced_tags(title, author, description, csv_tags, subjects):
    """Extract and classify tags into genres and moods"""
    
    # Clean and combine all available data
    all_tags = set()
    
    # Add OpenLibrary subjects
    if subjects:
        all_tags.update([s.lower() for s in subjects if s and len(s) > 2])
    
    # Add CSV shelf tags
    if csv_tags:
        all_tags.update(csv_tags)
    
    # Add title words (useful for genre clues)
    title_words = title.lower().split()
    meaningful_words = [w for w in title_words if len(w) > 3 and w not in ['the', 'and', 'for', 'with']]
    all_tags.update(meaningful_words[:5])
    
    # Classify genres and moods
    genres, moods = classify_genre_and_mood(
        list(all_tags),
        title,
        author,
        description
    )
    
    # Create final tag structure
    enhanced_tags = []
    
    # Add genre tags with prefix
    for genre in genres:
        enhanced_tags.append(f"genre: {genre}")
    
    # Add mood tags with prefix
    for mood in moods:
        enhanced_tags.append(f"mood: {mood}")
    
    # Add any remaining important tags from subjects
    important_subjects = [
        s for s in all_tags 
        if len(s) > 3 and 'fiction' not in s.lower()
        and not any(g in s.lower() for g in ['genre:', 'mood:'])
    ][:10]  # Limit to 10 additional tags
    
    enhanced_tags.extend(important_subjects)
    
    # Remove duplicates and sort
    return sorted(list(set(enhanced_tags)))

# -------- API Functions --------

def fetch_openlibrary_data(isbn, title, author):
    """Get data from OpenLibrary"""
    result = {"summary": "", "subjects": []}
    
    # Try ISBN first
    if isbn:
        try:
            url = f"https://openlibrary.org/isbn/{isbn}.json"
            res = requests.get(url, timeout=8)
            
            if res.status_code == 200:
                data = res.json()
                
                # Get description
                if "description" in data:
                    if isinstance(data["description"], dict):
                        result["summary"] = data["description"].get("value", "")
                    else:
                        result["summary"] = str(data["description"])
                
                # Get subjects
                result["subjects"] = [s.lower() for s in data.get("subjects", [])]
                
                return result
        except:
            pass
    
    # If ISBN fails, try search
    try:
        query = f"{title} {author}"
        url = f"https://openlibrary.org/search.json?q={quote(query)}&limit=1"
        res = requests.get(url, timeout=8)
        
        if res.status_code == 200:
            data = res.json()
            if data.get("docs"):
                doc = data["docs"][0]
                
                # Get work key for better description
                if "key" in doc:
                    work_key = doc["key"]
                    work_url = f"https://openlibrary.org{work_key}.json"
                    work_res = requests.get(work_url, timeout=8)
                    
                    if work_res.status_code == 200:
                        work_data = work_res.json()
                        if "description" in work_data:
                            if isinstance(work_data["description"], dict):
                                result["summary"] = work_data["description"].get("value", "")
                            else:
                                result["summary"] = str(work_data["description"])
                
                # Get subjects from search
                if "subject" in doc:
                    result["subjects"] = [s.lower() for s in doc["subject"][:15]]
                
                return result
    except:
        pass
    
    return result

def fetch_wikipedia_summary(title):
    """Get summary from Wikipedia"""
    try:
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={quote(f'{title} book')}&format=json"
        res = requests.get(search_url, timeout=8)
        
        if res.status_code != 200:
            return ""
        
        data = res.json()
        if not data.get("query", {}).get("search"):
            return ""
        
        page_title = data["query"]["search"][0]["title"]
        
        extract_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&exintro&explaintext&titles={quote(page_title)}&format=json"
        res = requests.get(extract_url, timeout=8)
        
        if res.status_code != 200:
            return ""
        
        data = res.json()
        pages = data.get("query", {}).get("pages", {})
        
        for page_data in pages.values():
            if "extract" in page_data:
                paragraphs = page_data["extract"].split("\n")
                for p in paragraphs:
                    if len(p) > 50:
                        return p[:400] + ("..." if len(p) > 400 else "")
        
        return ""
        
    except Exception:
        return ""

def extract_tags_from_csv(row):
    """Extract tags from CSV data"""
    tags = []
    
    # From bookshelves
    if "Bookshelves" in row and row["Bookshelves"]:
        shelves = row["Bookshelves"].split(",")
        tags.extend([s.strip().lower() for s in shelves if s.strip()])
    
    # Add exclusive shelf status
    if "Exclusive Shelf" in row and row["Exclusive Shelf"]:
        tags.append(row["Exclusive Shelf"].lower())
    
    # Add other useful CSV columns if they exist
    if "My Rating" in row and row["My Rating"] and row["My Rating"] != "0":
        tags.append(f"rated: {row['My Rating']}/5")
    
    return tags

# -------- Main Processing --------

print("📚 Reading your Goodreads export...")

books = []
total_books = 0
to_read_books = 0

# Read CSV and filter for "to-read" shelf
with open(f"goodreads_{USER}library_export.csv", newline='', encoding="utf-8") as f:
    reader = csv.DictReader(f)
    
    for row in reader:
        total_books += 1
        
        # ONLY process books from "to-read" shelf
        if row["Exclusive Shelf"] == "to-read":
            to_read_books += 1
            original_title = row["Title"].strip()
            
            books.append({
                "title": original_title,
                "search_title": clean_series_title(original_title),
                "series": extract_series(original_title),
                "author": row["Author"].strip(),
                "number_of_pages": row["Number of Pages"].strip(),
                "isbn": clean_isbn(row["ISBN13"]) or clean_isbn(row["ISBN"]),
                "csv_row": row
            })

print(f"📊 Found {total_books} total books in your export")
print(f"📖 Found {to_read_books} books on your 'to-read' shelf")
print(f"🔄 Starting enrichment process...\n")

# Enrich books
enriched_books = []

for i, book in enumerate(books):
    print(f"[{i+1}/{len(books)}] Processing: {book['title']}")
    
    # Get data from OpenLibrary
    ol_data = fetch_openlibrary_data(
        book["isbn"],
        book["search_title"],
        book["author"]
    )
    
    summary = ol_data["summary"]
    subjects = ol_data["subjects"]
    
    # Try Wikipedia if no summary
    if not summary or len(summary) < 30:
        wiki_summary = fetch_wikipedia_summary(book["search_title"])
        if wiki_summary and len(wiki_summary) > len(summary):
            summary = wiki_summary
    
    # Get CSV tags
    csv_tags = extract_tags_from_csv(book["csv_row"])
    
    # Enhanced tag extraction with genre and mood
    enhanced_tags = extract_enhanced_tags(
        book["title"],
        book["author"],
        summary,
        csv_tags,
        subjects
    )
    
    # If still no summary, create a basic one
    if not summary:
        summary = f"'{book['title']}' by {book['author']}."
    
    enriched_books.append({
        "title": book["title"],
        "series": book["series"],
        "author": book["author"],
        "pages": book["number_of_pages"],
        "tags": enhanced_tags,
        "summary": summary,
        "isbn": book["isbn"]
    })
    
    time.sleep(0.8)

# Save results
with open(f"{USER}_books_enriched.json", "w", encoding="utf-8") as f:
    json.dump(enriched_books, f, indent=2, ensure_ascii=False)

print(f"\n" + "="*50)
print(f"✅ Done! Processed {len(enriched_books)} books from your 'to-read' shelf.")
print(f"📁 Output saved to {USER}_books_enriched.json")

# Print stats
books_with_summary = sum(1 for b in enriched_books if b["summary"] and len(b["summary"]) > 20)
books_with_genre_tags = sum(1 for b in enriched_books if any("genre:" in tag for tag in b["tags"]))
books_with_mood_tags = sum(1 for b in enriched_books if any("mood:" in tag for tag in b["tags"]))

print(f"\n📊 Stats:")
print(f"  • Books with summaries: {books_with_summary}/{len(enriched_books)}")
print(f"  • Books with genre tags: {books_with_genre_tags}/{len(enriched_books)}")
print(f"  • Books with mood tags: {books_with_mood_tags}/{len(enriched_books)}")

# Show sample of first 3 books
print(f"\n📖 Sample of first 3 enriched books:")
for i, book in enumerate(enriched_books[:3]):
    print(f"\n  {i+1}. {book['title']}")
    print(f"     Author: {book['author']}")
    print(f"     Pages: {book['pages']}")
    
    # Show genre and mood tags
    genre_tags = [t for t in book['tags'] if t.startswith('genre:')]
    mood_tags = [t for t in book['tags'] if t.startswith('mood:')]
    other_tags = [t for t in book['tags'] if not t.startswith('genre:') and not t.startswith('mood:')]
    
    if genre_tags:
        print(f"     Genres: {', '.join([t.replace('genre: ', '') for t in genre_tags])}")
    if mood_tags:
        print(f"     Moods: {', '.join([t.replace('mood: ', '') for t in mood_tags])}")
    if other_tags:
        print(f"     Other tags: {', '.join(other_tags[:5])}")
    
    summary_preview = book['summary'][:150] + "..." if len(book['summary']) > 150 else book['summary']
    print(f"     Summary: {summary_preview}")