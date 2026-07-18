from mock_ad_connector import MockActiveDirectoryConnector


def main() -> None:
    connector = MockActiveDirectoryConnector()

    user = connector.find_user_by_employee_id("E1002")

    if user:
        print("Mock AD user found:")
        print(f"  Name:       {user['display_name']}")
        print(f"  Department: {user['department']}")
        print(f"  Role:       {user['title']}")
        print(f"  Enabled:    {user['enabled']}")
        print("  Groups:")

        for group in connector.get_user_groups("E1002"):
            print(f"    - {group}")
    else:
        print("User not found.")

    group = connector.find_group_by_name("GG-QA-Engineers")

    if group:
        print("\nMock AD group found:")
        print(f"  Name: {group['name']}")
        print(f"  DN:   {group['distinguished_name']}")


if __name__ == "__main__":
    main()