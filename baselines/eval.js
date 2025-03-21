const { execSync } = require('child_process');
const fs = require('fs');

const topPackages = ['express', 'debug', 'fs-extra', 'prop-types', 'react-dom'];

const measureTime = (fn) => {
    const start = process.hrtime();
    fn();
    const end = process.hrtime(start);
    return (end[0] + end[1] / 1e9).toFixed(2);
};

const getStorageUsage = () => {
    try {
        execSync('sync');
        const size = execSync('du -sm ./app/test', { encoding: 'utf8' }).split("\t")[0];
        return parseFloat(size);
    } catch (error) {
        console.error("Storage measuring error: ", error);
        return -1;
    }
};

const testPackageDynamic = (pkg) => {
    execSync('rm -rf ./app', { stdio: 'inherit' });
    execSync('mkdir -p ./app/test', { stdio: 'inherit' });
    execSync('chmod 777 ./app/test', { stido: 'inherit' });
    execSync(`cd ./app/test && npm show ${pkg} --json > package.json`, { stdio: 'inherit' });
    let pkgjson = JSON.parse(fs.readFileSync('./app/test/package.json'));
    pkgjson.bundleDependencies = 'false';
    fs.writeFileSync('./app/test/package.json', JSON.stringify(pkgjson, null, 2));
    execSync('chmod 777 ./app/test/package.json', { stido: 'inherit' });
    execSync('cd ./app/test && npm pack && npm init -y', {stdio: 'inherit'});
    const beforeDynamicSize = getStorageUsage();
    const dynamicTime = measureTime(() => {
        execSync(`npm install *.tgz --force`, { cwd: './app/test', stdio: 'ignore' });
    });
    const afterDynamicSize = getStorageUsage();
    const dynamicStorage = (afterDynamicSize - beforeDynamicSize).toFixed(2);

    return {
        package: pkg,
        dynamic: { time: dynamicTime, storage: dynamicStorage }
    };
};

const testPackageStatic = (pkg) => {
    execSync('rm -rf ./app', { stdio: 'inherit' });
    execSync('mkdir -p ./app/test', { stdio: 'inherit' });
    execSync('chmod 777 ./app/test', { stido: 'inherit' });
    execSync(`cd ./app/test && npm show ${pkg} --json > package.json`, { stdio: 'inherit' });
    let pkgjson = JSON.parse(fs.readFileSync('./app/test/package.json'));
    pkgjson.bundleDependencies = 'true';
    fs.writeFileSync('./app/test/package.json', JSON.stringify(pkgjson, null, 2));
    execSync('chmod 777 ./app/test/package.json', { stido: 'inherit' });
    execSync('cd ./app/test && npm pack && npm init -y', {stdio: 'inherit'});
    const beforeStaticSize = getStorageUsage();
    const staticTime = measureTime(() => {
        execSync(`npm install *.tgz --force`, { cwd: './app/test', stdio: 'ignore' });
    });
    const afterStaticSize = getStorageUsage();
    const staticStorage = (afterStaticSize - beforeStaticSize).toFixed(2);

    return {
        package: pkg,
        static: { time: staticTime, storage: staticStorage }
    };
}

// execSync('rm -rf ./app', { stdio: 'inherit' });
// execSync('mkdir -p ./app/test', { stdio: 'inherit' });
const resultsDynamic = [];
const resultsStatic = [];

for (const packageName of topPackages) {
    const result = testPackageDynamic(packageName);
    resultsDynamic.push(result);
}

// execSync('rm -rf ./app', { stdio: 'inherit' });
// execSync('mkdir -p ./app/test', { stdio: 'inherit' });

for (const packageName of topPackages) {
    const result = testPackageStatic(packageName);
    resultsStatic.push(result);
}

const merged = {};
const addtoMerged = (item) => {
    const key = item.package;
    if(!merged[key]) {
        merged[key] = { package: key };
    }
    Object.assign(merged[key], item);
}

resultsDynamic.forEach(addtoMerged);
resultsStatic.forEach(addtoMerged);

const results = Object.values(merged);

fs.writeFileSync('install_results.json', JSON.stringify(results, null, 2), 'utf8');

console.log("results saved to install_results.json!");
