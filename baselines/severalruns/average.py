import json
import glob

jsonFiles = glob.glob("./*.json")

aggregated = {
    "dynamic": {"sum": 0, "count": 0},
    "static": {"sum": 0, "count": 0}
}
numFiles = len(jsonFiles)
for file in jsonFiles:
    with open(file, 'r') as f:
        data = json.load(f)
        for entry in data:
            for category in ["dynamic", "static"]:
                timeValue = entry[category]["time"]
                timeValue = float(timeValue)
                aggregated[category]["sum"] += timeValue
                aggregated[category]["count"] += 1

avgData = {
    "dynamicAvg": aggregated["dynamic"]["sum"] / aggregated["dynamic"]["count"],
    "staticAvg": aggregated["static"]["sum"] / aggregated["dynamic"]["count"]
}

print(json.dumps(avgData, indent = 4))
with open("averaged_output.json", "w") as outFile:
    json.dump(avgData, outFile, indent = 4)
