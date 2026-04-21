from pprint import pprint

from app.db.repositories import (
    get_distinct_user_statuses,
    get_recent_news_sample,
    get_sent_article_links_for_email,
    get_user_categories_map,
    get_users_with_email,
)


def main():
    print("\n=== DISTINCT USER STATUSES ===")
    pprint(get_distinct_user_statuses())

    users = get_users_with_email()
    print(f"\n=== USERS WITH EMAIL === {len(users)} found")
    pprint(users[:5])

    category_map = get_user_categories_map()
    print(f"\n=== USERS WITH CATEGORY LINKS === {len(category_map)} found")

    if users:
        first_user = users[0]
        print("\n=== FIRST USER ===")
        pprint(first_user)

        user_categories = category_map.get(first_user["id"], [])
        print("\n=== FIRST USER CATEGORIES ===")
        pprint(user_categories)

        sent_links = get_sent_article_links_for_email(first_user["email"])
        print("\n=== FIRST USER SENT LINKS COUNT ===")
        print(len(sent_links))

    print("\n=== RECENT NEWS SAMPLE ===")
    pprint(get_recent_news_sample(10))


if __name__ == "__main__":
    main()