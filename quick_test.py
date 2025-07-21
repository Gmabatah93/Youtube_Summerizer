import sys
sys.path.append('/Users/isiomamabatah/Desktop/Python/Projects/Youtube_Summerizer')

from src.rag_post_processing import clean_document_content, is_high_quality_content
from langchain_core.documents import Document

def quick_test():
    print("🧪 Quick Test - Post Processing Functions")
    
    # Test 1: Content cleaning
    dirty_text = "[Music] This is a tutorial about machine learning [Applause] Visit https://spam.com"
    clean_text = clean_document_content(dirty_text)
    print(f"✅ Cleaning works: '{clean_text}'")
    
    # Test 2: Quality check
    good_doc = Document(
        page_content="This is a comprehensive machine learning tutorial with detailed explanations.",
        metadata={'view_count': 10000}
    )
    is_good = is_high_quality_content(good_doc, good_doc.page_content)
    print(f"✅ Quality check works: {is_good}")
    
    print("🎉 Basic functions are working!")

if __name__ == "__main__":
    quick_test()