thonimport json
import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

import requests

from .metrics_calculator import (
    compute_average_comments,
    compute_average_likes,
    compute_average_views,
    compute_engagement_rate,
)

LOGGER = logging.getLogger("instagram_profile_scraper_pro.parser")

@dataclass
class RecentPostMetrics:
    likes: int
    comments: int
    views: Optional[int] = None

@dataclass
class ProfileData:
    username: str
    fullName: Optional[str] = None
    followersCount: Optional[int] = None
    followsCount: Optional[int] = None
    engagementRate: Optional[float] = None
    averageLikes: Optional[float] = None
    averageComments: Optional[float] = None
    averageViews: Optional[float] = None
    profilePictureUrl: Optional[str] = None
    bio: Optional[str] = None
    website: Optional[str] = None
    category: Optional[str] = None
    recentPosts: List[RecentPostMetrics] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        # Convert dataclass to a JSON-serialisable dict with nested posts converted
        data = asdict(self)
        data["recentPosts"] = [
            {"likes": p.likes, "comments": p.comments, "views": p.views}
            for p in self.recentPosts
        ]
        return data

def _build_headers(settings: Dict[str, Any]) -> Dict[str, str]:
    ua = settings.get(
        "user_agent",
        "Mozilla/5.0 (compatible; InstagramProfileScraperPro/1.0)",
    )
    return {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

def _request_url(url: str, settings: Dict[str, Any]) -> Optional[str]:
    timeout = float(settings.get("request_timeout", 10))
    headers = _build_headers(settings)
    try:
        LOGGER.debug("Requesting URL: %s", url)
        response = requests.get(url, headers=headers, timeout=timeout)
        if response.status_code != 200:
            LOGGER.warning("Non-200 status code %s for URL %s", response.status_code, url)
            return None
        return response.text
    except requests.RequestException as exc:
        LOGGER.error("Request to %s failed: %s", url, exc)
        return None

def _extract_shared_data_from_html(html: str) -> Optional[Dict[str, Any]]:
    """
    Attempts to extract the embedded JSON data from the Instagram HTML.

    This is a best-effort parser; Instagram's internal structure may change.
    """
    # Try to find a JSON object assigned to window._sharedData or similar structures
    shared_data_match = re.search(
        r"window\._sharedData\s*=\s*(\{.*?\});</script>",
        html,
        flags=re.DOTALL,
    )
    if not shared_data_match:
        # Newer layouts often have "application/ld+json" blocks; try those as a fallback
        ld_json_match = re.search(
            r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>',
            html,
            flags=re.DOTALL,
        )
        if not ld_json_match:
            LOGGER.debug("No embedded JSON data found in HTML.")
            return None
        json_text = ld_json_match.group(1)
    else:
        json_text = shared_data_match.group(1)

    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        LOGGER.debug("Failed to decode embedded JSON.")
        return None

def _parse_profile_from_shared_data(username: str, data: Dict[str, Any]) -> ProfileData:
    """
    Parse profile information from the shared JSON-like data structure.
    This implementation targets common structures but is defensive.
    """
    # The structure of sharedData has changed many times; we navigate conservatively.
    user_data: Dict[str, Any] = {}

    # Attempt several known paths
    try_paths = [
        # Older structure
        ("entry_data", "ProfilePage", 0, "graphql", "user"),
        # Sometimes user object is exposed directly
        ("graphql", "user"),
    ]

    for path in try_paths:
        cur: Any = data
        try:
            for key in path:
                cur = cur[key]  # type: ignore[index]
            if isinstance(cur, dict) and cur.get("username"):
                user_data = cur
                break
        except (KeyError, IndexError, TypeError):
            continue

    if not user_data:
        # Fallback: build minimally populated profile
        LOGGER.warning("Could not locate user data for '%s' in shared data.", username)
        return ProfileData(username=username)

    # Followers / follows
    followers = None
    follows = None
    try:
        followers = int(user_data.get("edge_followed_by", {}).get("count"))
    except (TypeError, ValueError):
        pass

    try:
        follows = int(user_data.get("edge_follow", {}).get("count"))
    except (TypeError, ValueError):
        pass

    # Recent posts metrics
    recent_posts: List[RecentPostMetrics] = []
    edges = (
        user_data.get("edge_owner_to_timeline_media", {})
        .get("edges", [])
    )
    for edge in edges:
        node = edge.get("node") or {}
        try:
            likes = int(
                node.get("edge_liked_by", {}).get("count")
                or node.get("edge_media_preview_like", {}).get("count")
                or 0
            )
        except (TypeError, ValueError):
            likes = 0

        try:
            comments = int(
                node.get("edge_media_to_comment", {}).get("count") or 0
            )
        except (TypeError, ValueError):
            comments = 0

        # Video views (if any)
        views = None
        try:
            if node.get("__typename") == "GraphVideo":
                views_val = node.get("video_view_count")
                if views_val is not None:
                    views = int(views_val)
        except (TypeError, ValueError):
            views = None

        recent_posts.append(RecentPostMetrics(likes=likes, comments=comments, views=views))

    profile = ProfileData(
        username=username,
        fullName=user_data.get("full_name") or None,
        followersCount=followers,
        followsCount=follows,
        profilePictureUrl=user_data.get("profile_pic_url_hd")
        or user_data.get("profile_pic_url")
        or None,
        bio=user_data.get("biography") or None,
        website=user_data.get("external_url") or None,
        category=user_data.get("category_name") or None,
        recentPosts=recent_posts,
    )

    # Compute metrics
    if followers and followers > 0 and recent_posts:
        profile.averageLikes = compute_average_likes(recent_posts)
        profile.averageComments = compute_average_comments(recent_posts)
        profile.averageViews = compute_average_views(recent_posts)
        profile.engagementRate = compute_engagement_rate(recent_posts, followers)
    else:
        profile.averageLikes = compute_average_likes(recent_posts)
        profile.averageComments = compute_average_comments(recent_posts)
        profile.averageViews = compute_average_views(recent_posts)
        profile.engagementRate = None

    return profile

def fetch_profile(username: str, settings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Fetches and parses a public Instagram profile into the structured
    ProfileData format and returns it as a dictionary.

    Returns None if the profile could not be retrieved or parsed.
    """
    base_url = "https://www.instagram.com"
    profile_url = f"{base_url}/{username}/"

    html = _request_url(profile_url, settings)
    if html is None:
        LOGGER.error("Failed to retrieve HTML for profile '%s'.", username)
        return None

    shared_data = _extract_shared_data_from_html(html)
    if not shared_data:
        LOGGER.error("Failed to locate embedded JSON for profile '%s'.", username)
        # Return at least a minimal profile object
        return ProfileData(username=username).to_dict()

    profile = _parse_profile_from_shared_data(username, shared_data)
    max_posts = int(settings.get("max_posts", 12))
    if profile.recentPosts and len(profile.recentPosts) > max_posts:
        profile.recentPosts = profile.recentPosts[:max_posts]

    return profile.to_dict()