thonfrom typing import Any, Dict, List

import pandas as pd

def profile_to_row(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flattens the profile dict to a single-row dict suitable for a CSV row.
    The recentPosts list is not expanded; this focuses on top-level metrics.
    """
    # Copy only the documented top-level fields
    row = {
        "username": profile.get("username"),
        "fullName": profile.get("fullName"),
        "followersCount": profile.get("followersCount"),
        "followsCount": profile.get("followsCount"),
        "engagementRate": profile.get("engagementRate"),
        "averageLikes": profile.get("averageLikes"),
        "averageComments": profile.get("averageComments"),
        "averageViews": profile.get("averageViews"),
        "profilePictureUrl": profile.get("profilePictureUrl"),
        "bio": profile.get("bio"),
        "website": profile.get("website"),
        "category": profile.get("category"),
    }
    return row

def profiles_to_table(profiles: List[Dict[str, Any]]) -> pd.DataFrame:
    rows = [profile_to_row(p) for p in profiles]
    return pd.DataFrame(rows)