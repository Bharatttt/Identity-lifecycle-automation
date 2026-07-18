from rbac import get_required_groups, load_rbac_mapping


if __name__ == "__main__":
    mapping = load_rbac_mapping()

    requested_access = get_required_groups(
        department="Engineering",
        role="Software Engineer",
        mapping=mapping,
    )

    print("AD groups:")
    for group in requested_access["ad_groups"]:
        print(f"  - {group}")

    print("\nEntra groups:")
    for group in requested_access["entra_groups"]:
        print(f"  - {group}")