import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [activeTab, setActiveTab] = useState("global");
  const [news, setNews] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedState, setSelectedState] = useState("");
  const [states, setStates] = useState({});
  const [error, setError] = useState("");

  const indianStates = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Jammu and Kashmir", "Ladakh", "Delhi", "Puducherry"
  ];

  useEffect(() => {
    fetchNews("global");
    fetchStates();
  }, []);

  const fetchStates = async () => {
    try {
      const response = await axios.get(`${API}/states`);
      setStates(response.data.states);
    } catch (error) {
      console.error("Error fetching states:", error);
    }
  };

  const fetchNews = async (type, stateName = "") => {
    setLoading(true);
    setError("");
    
    try {
      let url = "";
      switch (type) {
        case "global":
          url = `${API}/news/global`;
          break;
        case "india":
          url = `${API}/news/india`;
          break;
        case "state":
          url = `${API}/news/state/${stateName.toLowerCase().replace(/ /g, "-")}`;
          break;
        default:
          url = `${API}/news/global`;
      }

      const response = await axios.get(url);
      setNews(response.data.news || []);
    } catch (error) {
      console.error("Error fetching news:", error);
      setError("Failed to fetch news. Please try again.");
      setNews([]);
    } finally {
      setLoading(false);
    }
  };

  const searchNews = async () => {
    if (!searchQuery.trim()) return;
    
    setLoading(true);
    setError("");
    
    try {
      const response = await axios.get(`${API}/news/search`, {
        params: { q: searchQuery }
      });
      setNews(response.data.news || []);
      setActiveTab("search");
    } catch (error) {
      console.error("Error searching news:", error);
      setError("Failed to search news. Please try again.");
      setNews([]);
    } finally {
      setLoading(false);
    }
  };

  const refreshNews = async () => {
    setLoading(true);
    try {
      await axios.post(`${API}/news/refresh`);
      await fetchNews(activeTab === "state" ? "state" : activeTab, selectedState);
    } catch (error) {
      console.error("Error refreshing news:", error);
      setError("Failed to refresh news. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    if (tab === "global" || tab === "india") {
      fetchNews(tab);
      setSelectedState("");
    }
  };

  const handleStateChange = (state) => {
    setSelectedState(state);
    setActiveTab("state");
    fetchNews("state", state);
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    });
  };

  const getCategoryBadgeColor = (category) => {
    const colors = {
      politics: "bg-red-100 text-red-800",
      economy: "bg-green-100 text-green-800",
      education: "bg-blue-100 text-blue-800",
      science: "bg-purple-100 text-purple-800",
      environment: "bg-emerald-100 text-emerald-800",
      sports: "bg-orange-100 text-orange-800",
      health: "bg-pink-100 text-pink-800",
      defense: "bg-gray-100 text-gray-800",
      general: "bg-gray-100 text-gray-800"
    };
    return colors[category] || colors.general;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-lg border-b-4 border-indigo-600">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between">
            <div className="mb-4 md:mb-0">
              <h1 className="text-3xl font-bold text-gray-900">
                📰 Current Affairs Hub
              </h1>
              <p className="text-gray-600 mt-1">
                Educational platform for UPSC & State-level exam preparation
              </p>
            </div>
            
            {/* Search Bar */}
            <div className="flex gap-2 max-w-md">
              <input
                type="text"
                placeholder="Search news (e.g., 'NEET exam', 'economy')"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === "Enter" && searchNews()}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              />
              <button
                onClick={searchNews}
                className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
              >
                🔍
              </button>
            </div>
          </div>
          
          {/* Navigation Tabs */}
          <div className="mt-6 flex flex-wrap gap-2">
            <button
              onClick={() => handleTabChange("global")}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === "global"
                  ? "bg-indigo-600 text-white"
                  : "bg-gray-200 text-gray-700 hover:bg-gray-300"
              }`}
            >
              🌍 Global News
            </button>
            <button
              onClick={() => handleTabChange("india")}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === "india"
                  ? "bg-indigo-600 text-white"
                  : "bg-gray-200 text-gray-700 hover:bg-gray-300"
              }`}
            >
              🇮🇳 India News
            </button>
            
            {/* State Selector */}
            <select
              value={selectedState}
              onChange={(e) => handleStateChange(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white"
            >
              <option value="">Select Indian State</option>
              {indianStates.map((state) => (
                <option key={state} value={state}>
                  {state}
                </option>
              ))}
            </select>
            
            <button
              onClick={refreshNews}
              disabled={loading}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
            >
              🔄 Refresh
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Status Bar */}
        <div className="mb-6 p-4 bg-white rounded-lg shadow-sm border-l-4 border-indigo-500">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                {activeTab === "global" && "🌍 Global News"}
                {activeTab === "india" && "🇮🇳 India News"}
                {activeTab === "state" && `📍 ${selectedState} News`}
                {activeTab === "search" && `🔍 Search Results for "${searchQuery}"`}
              </h2>
              <p className="text-sm text-gray-600">
                {news.length} articles found
                {loading && " • Loading..."}
              </p>
            </div>
            
            {selectedState && states[selectedState] && (
              <div className="mt-2 sm:mt-0">
                <p className="text-sm text-gray-600">
                  <strong>Districts:</strong> {states[selectedState].join(", ")}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border-l-4 border-red-500 rounded-lg">
            <p className="text-red-700">{error}</p>
          </div>
        )}

        {/* Loading Spinner */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
          </div>
        )}

        {/* News Grid */}
        {!loading && news.length > 0 && (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {news.map((article, index) => (
              <article
                key={article.id || index}
                className="bg-white rounded-xl shadow-lg overflow-hidden hover:shadow-xl transition-shadow duration-300 border border-gray-200"
              >
                <div className="p-6">
                  {/* Category and State Badges */}
                  <div className="flex flex-wrap gap-2 mb-3">
                    {article.category && (
                      <span
                        className={`px-2 py-1 text-xs font-medium rounded-full ${getCategoryBadgeColor(
                          article.category
                        )}`}
                      >
                        {article.category.charAt(0).toUpperCase() + article.category.slice(1)}
                      </span>
                    )}
                    {article.state && (
                      <span className="px-2 py-1 text-xs font-medium rounded-full bg-indigo-100 text-indigo-800">
                        📍 {article.state}
                      </span>
                    )}
                    {article.district && (
                      <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800">
                        🏘️ {article.district}
                      </span>
                    )}
                  </div>

                  {/* Title */}
                  <h3 className="text-lg font-semibold text-gray-900 mb-3 line-clamp-3">
                    {article.title}
                  </h3>

                  {/* Summary */}
                  {article.summary && article.summary !== article.title && (
                    <p className="text-gray-600 text-sm mb-4 line-clamp-3">
                      {article.summary}
                    </p>
                  )}

                  {/* Footer */}
                  <div className="flex items-center justify-between text-sm text-gray-500">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{article.source}</span>
                      {article.is_global && (
                        <span className="text-xs bg-blue-100 text-blue-600 px-2 py-1 rounded">
                          Global
                        </span>
                      )}
                    </div>
                    <time dateTime={article.published_at}>
                      {formatDate(article.published_at)}
                    </time>
                  </div>

                  {/* Read More Link */}
                  {article.url && (
                    <div className="mt-4">
                      <a
                        href={article.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center text-indigo-600 hover:text-indigo-800 font-medium text-sm"
                      >
                        Read Full Article →
                      </a>
                    </div>
                  )}
                </div>
              </article>
            ))}
          </div>
        )}

        {/* No Results */}
        {!loading && news.length === 0 && !error && (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">📰</div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              No news articles found
            </h3>
            <p className="text-gray-600 mb-4">
              {activeTab === "search"
                ? `No articles found for "${searchQuery}". Try different keywords.`
                : "No articles available at the moment. Try refreshing or check back later."}
            </p>
            <button
              onClick={refreshNews}
              className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
            >
              🔄 Refresh News
            </button>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;