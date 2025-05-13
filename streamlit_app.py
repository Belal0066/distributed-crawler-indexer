import streamlit as st
import requests

# Base URL of your FastAPI backend (master node)
MASTER_URL = "http://13.61.155.34:8000"

st.set_page_config(page_title="Crawler Dashboard", layout="wide")
st.title("🌐 Distributed Web Crawler and Indexing System")

tab1, tab2, tab3, tab4 = st.tabs(["Start Crawl", "Status", "Search", "System Health"])

with tab1:
    st.header("Start New Crawl")
    urls = st.text_area("Seed URLs (one per line)")
    depth = st.slider("Crawl Depth", 1, 10, 2)
    max_pages = st.number_input("Maximum Pages", 1, 10000, 100)
    delay = st.number_input("Delay Between Requests (seconds)", 0.0, 10.0, 1.0)

    st.markdown("### Optional: Allowed Domains")
    domains_input = st.text_area("Allowed Domains (one per line)", placeholder="example.com")
    domains = [d.strip() for d in domains_input.splitlines() if d.strip()]

    respect_robots = st.checkbox("Respect robots.txt", value=True)

    if st.button("🚀 Start Crawl"):
        config = {
            "urls": [u.strip() for u in urls.strip().splitlines() if u.strip()],
            "depth": depth,
            "allowed_domains": domains,
            "respect_robots": respect_robots,
            "max_pages": max_pages,
            "delay": delay
        }
        try:
            response = requests.post(f"{MASTER_URL}/crawl", json=config, timeout=20)
            if response.ok:
                job_id = response.json().get("job_id")
                st.success(f"Crawl started successfully! Job ID: {job_id}")
            else:
                st.error(f"Failed to start crawl: {response.text}")
        except Exception as e:
            st.error(f"Error: {e}")

with tab2:
    st.header("Check Crawl Status")
    job_id = st.text_input("Enter Job ID to Check Status")
    if st.button("🔍 Get Status"):
        try:
            response = requests.get(f"{MASTER_URL}/job/{job_id}", timeout=10)
            if response.ok:
                st.json(response.json())
            else:
                st.error(f"Error: {response.status_code} - {response.text}")
        except Exception as e:
            st.error(f"Request failed: {e}")

with tab3:
    st.header("Search Indexed Content")
    query = st.text_input("Enter Search Query")
    search_type = st.selectbox("Search Type", ["match", "phrase", "boolean"])
    if st.button("🔎 Search"):
        try:
            response = requests.post(f"{MASTER_URL}/search", json={"query": query, "search_type": search_type}, timeout=10)
            if response.ok:
                results = response.json()
                if not results:
                    st.info("No results found.")
                for i, r in enumerate(results, 1):
                    st.markdown(f"### {i}. {r.get('title', 'No Title')}")
                    st.write(f"**URL:** {r.get('url', 'N/A')}")
                    st.write(f"**Relevance Score:** {r.get('score', 0):.2f}")
                    st.write(r.get("summary", "No snippet available"))
                    st.markdown("---")
            else:
                st.error(f"Search failed: {response.status_code}")
        except Exception as e:
            st.error(f"Search request failed: {e}")

with tab4:
    st.header("System Health Check")
    if st.button("🩺 Check System Health"):
        try:
            response = requests.get(f"{MASTER_URL}/health", timeout=10)
            if response.ok:
                st.json(response.json())
            else:
                st.error(f"Failed to fetch health: {response.status_code}")
        except Exception as e:
            st.error(f"Error: {e}")
