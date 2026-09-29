// Optional fallback: install Playwright in a run-local tools folder, never in the skill.
// node capture.mjs --url http://127.0.0.1:PORT --out RUN/screenshots --module /absolute/path/to/playwright/index.mjs
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
const args = Object.fromEntries(process.argv.slice(2).reduce((a, v, i, all) => i % 2 === 0 ? [...a, [v.replace(/^--/, ''), all[i+1]]] : a, []));
if (!args.url || !args.out || !/^https?:\/\//.test(args.url)) throw new Error('--url HTTP(S) and --out are required');
const pw = args.module ? await import(pathToFileURL(path.resolve(args.module)).href) : await import('playwright');
const browser = await pw.chromium.launch({headless:true, ...(args.executable ? {executablePath:path.resolve(args.executable)} : {})});
await fs.mkdir(args.out, {recursive:true});
const report = {url:args.url, captured_at:new Date().toISOString(), views:[], note:'Visual inspection and business-content checks still required.'};
try {
  for (const [name, width, height] of [['desktop',1440,1050],['mobile',390,844]]) {
    const page = await browser.newPage({viewport:{width,height}, deviceScaleFactor:1});
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto(args.url, {waitUntil:'networkidle',timeout:30000});
    await page.screenshot({path:path.join(args.out, `${name}.png`), fullPage:true});
    const layout = await page.evaluate(() => ({overflow:document.documentElement.scrollWidth > window.innerWidth+1,title:document.title}));
    report.views.push({name,width,height,path:`${name}.png`,errors,...layout});
    await page.close();
  }
} finally { await browser.close(); }
await fs.writeFile(path.join(args.out,'capture-report.json'), JSON.stringify(report,null,2));
console.log(JSON.stringify(report,null,2));
if (report.views.some(v => v.overflow || v.errors.length)) process.exitCode = 2;
