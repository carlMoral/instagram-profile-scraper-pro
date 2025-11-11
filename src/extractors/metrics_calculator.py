thonfrom typing import List, Optional

from .instagram_parser import RecentPostMetrics

def compute_average_likes(posts: List[RecentPostMetrics]) -> Optional[float]:
    if not posts:
        return None
    total = sum(p.likes for p in posts)
    return round(total / len(posts), 2)

def compute_average_comments(posts: List[RecentPostMetrics]) -> Optional[float]:
    if not posts:
        return None
    total = sum(p.comments for p in posts)
    return round(total / len(posts), 2)

def compute_average_views(posts: List[RecentPostMetrics]) -> Optional[float]:
    views = [p.views for p in posts if p.views is not None]
    if not views:
        return None
    total = sum(views)
    return round(total / len(views), 2)

def compute_engagement_rate(
    posts: List[RecentPostMetrics],
    followers_count: int,
) -> Optional[float]:
    """
    Engagement rate in percentage based on:
    (total likes + total comments) / (followers * number_of_posts) * 100
    """
    if not posts or not followers_count:
        return None

    total_likes = sum(p.likes for p in posts)
    total_comments = sum(p.comments for p in posts)
    denominator = followers_count * len(posts)
    if denominator == 0:
        return None