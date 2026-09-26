import pandas as pd

projects = pd.read_csv("projects.csv")

print("Number of projects:", len(projects))

print("\nProjects loaded:")

for index, project in projects.iterrows():

    print("--------------------")
    print("Project ID:", project["project_id"])
    print("Project:", project["project_name"])
    print("Type:", project["project_type"])
    print("Location 1:", project["location_1"])
    print("Location 2:", project["location_2"])