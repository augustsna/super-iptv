import puppeteer from 'puppeteer';
import fs from 'fs';

(async () => {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();
    
    const svgContent = fs.readFileSync('public/favicon.svg', 'utf8');
    
    await page.setContent(`
        <html>
            <body style="margin:0; padding:0; background: transparent;">
                <div style="width: 256px; height: 256px; display: flex; align-items: center; justify-content: center;">
                    ${svgContent.replace('<svg ', '<svg style="width: 100%; height: 100%;" ')}
                </div>
            </body>
        </html>
    `);
    
    const element = await page.$('div');
    await element.screenshot({ path: 'ac3 eac3/favicon.png', omitBackground: true });
    
    await browser.close();
    console.log("Done");
})();
