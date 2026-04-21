GET_ALL_CATEGORIES = """
SELECT
    c.id,
    c.name
FROM categories c
WHERE c.name IS NOT NULL
  AND TRIM(c.name) <> ''
ORDER BY c.name;
"""

GET_USERS_WITH_EMAIL = """
SELECT
    u.id,
    u.email,
    u.username,
    u.user_lang,
    u.status
FROM users u
WHERE u.email IS NOT NULL
  AND TRIM(u.email) <> ''
  AND u.status = 'active'
ORDER BY u.created_at;
"""

GET_USER_CATEGORIES = """
SELECT
    uc.user_id,
    c.id AS category_id,
    c.name AS category_name
FROM user_category uc
JOIN categories c
  ON c.id = uc.category_id
ORDER BY uc.user_id, c.name;
"""

GET_RECENT_NEWS_BY_CATEGORY = """
SELECT
    n.id,
    n.title,
    n.summary,
    n.insight,
    n.keywords,
    n.news_url,
    n.image_url,
    n.news_date,
    n.news_lang,
    n.category_id,
    c.name AS category_name
FROM news n
JOIN categories c
  ON c.id = n.category_id
WHERE n.user_id = %s
  AND n.category_id = %s
  AND n.news_lang = %s
  AND n.news_date = (NOW() AT TIME ZONE 'Asia/Baku')::date
ORDER BY n.created_at DESC, n.title ASC;
"""

GET_ALREADY_SENT_ARTICLE_LINKS_FOR_EMAIL = """
SELECT sa.article_link
FROM sent_articles sa
WHERE sa.user_email = %s
  AND (sa.sent_at AT TIME ZONE 'Asia/Baku')::date = (NOW() AT TIME ZONE 'Asia/Baku')::date;
"""

INSERT_SENT_ARTICLE = """
INSERT INTO sent_articles (
    id,
    article_link,
    article_title,
    sent_at,
    user_email
)
VALUES (
    gen_random_uuid(),
    %s,
    %s,
    NOW(),
    %s
)
ON CONFLICT (user_email, article_link) DO NOTHING;
"""

GET_ALL_SITES = """
SELECT site_url
FROM sites
WHERE site_url IS NOT NULL
  AND TRIM(site_url) <> ''
ORDER BY site_url;
"""

GET_ALL_SITE_IDS = """
SELECT uuid, site_url
FROM sites
WHERE site_url IS NOT NULL
  AND TRIM(site_url) <> '';
"""

GET_SITE_ID_BY_URL = """
SELECT uuid
FROM sites
WHERE site_url = %s
LIMIT 1;
"""

INSERT_SITE = """
INSERT INTO sites (uuid, site_url)
VALUES (gen_random_uuid(), %s)
RETURNING uuid;
"""

FIND_CATEGORY_ID_BY_EXACT_NAME = """
SELECT id
FROM categories
WHERE LOWER(name) = LOWER(%s)
LIMIT 1;
"""

FIND_CATEGORY_ID_BY_LIKE = """
SELECT id
FROM categories
WHERE LOWER(name) LIKE LOWER(%s)
ORDER BY LENGTH(name) ASC
LIMIT 1;
"""

INSERT_NEWS_ITEM_FOR_USER = """
INSERT INTO news (
    id,
    created_at,
    updated_at,
    image_url,
    insight,
    keywords,
    news_date,
    news_lang,
    news_url,
    sent_at,
    sites_id,
    summary,
    title,
    category_id,
    user_id
)
VALUES (
    gen_random_uuid(),
    NOW(),
    NOW(),
    %s,
    %s,
    %s,
    %s,
    %s,
    %s,
    NOW(),
    %s,
    %s,
    %s,
    %s,
    %s
)
ON CONFLICT ON CONSTRAINT uk_news_url_date_lang_user DO NOTHING;
"""
