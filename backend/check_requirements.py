import pkg_resources

def check_requirements(requirements_file="requirements.txt"):
    with open(requirements_file) as f:
        required = f.read().splitlines()
    installed = {pkg.key for pkg in pkg_resources.working_set}
    missing = [pkg for pkg in required if pkg.split("==")[0].lower() not in installed]
    if missing:
        print("Missing packages:", missing)
    else:
        print("All requirements satisfied.")

if __name__ == "__main__":
    check_requirements()