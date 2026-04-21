from pprint import pprint

from app.db.repositories import get_user_categories_map, get_users_with_email


def main():
    users = get_users_with_email()
    category_map = get_user_categories_map()

    for user in users:
        print("\n====================")
        print(f"USER: {user['username']} | {user['email']} | {user['id']}")
        pprint(category_map.get(user["id"], []))


if __name__ == "__main__":
    main()