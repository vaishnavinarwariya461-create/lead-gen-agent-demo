import streamlit as st
import pandas as pd
import requests
import random

# --- CONFIGURATION & SCORING LOGIC ---

def calculate_propensity_score(candidate):
    score = 0
    breakdown = []

    # 1. Role/Topic Fit (Weight: +30)
    title_lower = candidate['Title'].lower()
    target_roles = ['toxicology', 'safety', 'hepatic', '3d', 'liver', 'vitro']
    
    if any(keyword in title_lower for keyword in target_roles):
        score += 30
        breakdown.append("Role Fit (+30)")

    # 2. Scientific Intent (Weight: +40)
    score += 40
    breakdown.append("Scientific Intent (+40)")

    # 3. Location Hub (Weight: +10)
    hubs = ['boston', 'cambridge', 'bay area', 'basel', 'london', 'oxford']
    loc_lower = candidate.get('Enriched_Location', candidate.get('Affiliation', '')).lower()
    
    if any(hub in loc_lower for hub in hubs):
        score += 10
        breakdown.append("Hub Location (+10)")

    # 4. Company Intent/Funding (Weight: +20)
    if candidate.get('Enriched_Funding') in ['Series A', 'Series B', 'Public']:
        score += 20
        breakdown.append("Funding (+20)")

    return min(score, 100), ", ".join(breakdown)

# --- REAL DATA FETCHING (PubMed API) ---

@st.cache_data
def fetch_pubmed_leads(keyword="Drug-Induced Liver Injury"):
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    search_url = f"{base_url}/esearch.fcgi?db=pubmed&term={keyword}&retmode=json&retmax=15&sort=date"
    
    try:
        search_resp = requests.get(search_url).json()
        id_list = search_resp['esearchresult']['idlist']
        if not id_list: return []

        ids_str = ",".join(id_list)
        summary_url = f"{base_url}/esummary.fcgi?db=pubmed&id={ids_str}&retmode=json"
        summary_resp = requests.get(summary_url).json()
        
        leads = []
        uid_dict = summary_resp['result']
        
        for uid in id_list:
            if uid not in uid_dict: continue
            item = uid_dict[uid]
            authors = item.get('authors', [])
            if not authors: continue
            primary_author = authors[0]['name']
            
            leads.append({
                "Name": primary_author,
                "Title": item.get('title', 'No Title'),
                "Company": item.get('source', 'Unknown Journal'),
                "Affiliation": "Check LinkedIn", 
                "LinkedIn": f"https://www.linkedin.com/search/results/people/?keywords={primary_author}",
                "Enriched_Location": "",
                "Enriched_Funding": ""
            })
        return leads
    except Exception as e:
        st.error(f"Error connecting to PubMed: {e}")
        return []

# --- DASHBOARD UI ---

st.set_page_config(page_title="Lead Gen Agent", layout="wide")

st.title("🧬 Lead Gen Agent: Enrichment Demo")
st.markdown("**Objective:** Real-time identification and ranking of researchers for 3D In-Vitro Models.")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("Agent Controls")
st.sidebar.markdown("---")
# REPLACE [Your Name] BELOW WITH YOUR ACTUAL NAME
st.sidebar.markdown("### Built by [Neeraj Narwariya](https://www.linkedin.com/in/neeraj-narwariya-45a39b349)") 
st.sidebar.markdown("---")

search_term = st.sidebar.text_input("Topic Keyword", "Drug-Induced Liver Injury")
run_crawler = st.sidebar.button("1. Run Live Crawler")
enrich_data = st.sidebar.button("2. Enrich Data (Simulate)")

if 'leads_data' not in st.session_state:
    st.session_state.leads_data = []

if run_crawler:
    with st.spinner('Crawling PubMed...'):
        st.session_state.leads_data = fetch_pubmed_leads(search_term)

if enrich_data and st.session_state.leads_data:
    with st.spinner('Querying Business Intelligence APIs...'):
        for person in st.session_state.leads_data:
            if random.random() < 0.3:
                person['Enriched_Location'] = "Cambridge, MA"
                person['Enriched_Funding'] = "Series B"
                person['Company'] = "Apex Biopharma"
            elif random.random() < 0.5:
                 person['Enriched_Location'] = "Basel, Switzerland"
                 person['Enriched_Funding'] = "Grant Funded"

# PROCESSING & SCORING
if st.session_state.leads_data:
    processed_data = []
    for row in st.session_state.leads_data:
        score, reason = calculate_propensity_score(row)
        row['Probability Score'] = score
        row['Scoring Factors'] = reason
        processed_data.append(row)
    
    df = pd.DataFrame(processed_data)
    df = df.sort_values(by="Probability Score", ascending=False)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Leads", len(df))
    hot_leads = len(df[df['Probability Score'] > 80])
    col2.metric("Hot Leads (>80 Score)", hot_leads, delta=hot_leads)
    
    st.write(f"### Prioritized Candidates")
    
    display_cols = ["Probability Score", "Name", "Company", "Enriched_Location", "Enriched_Funding", "Scoring Factors"]
    st.dataframe(df[display_cols].style.background_gradient(subset=['Probability Score'], cmap="Greens"), use_container_width=True)
    
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Export Leads", csv, "leads.csv", "text/csv")
else:
    st.info("👈 Click **'Run Live Crawler'** to start.")