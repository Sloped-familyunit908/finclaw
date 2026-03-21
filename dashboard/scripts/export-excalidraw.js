// Export Excalidraw file to PNG using Playwright
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  // Load excalidraw
  await page.goto('https://excalidraw.com', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);
  
  // Read our .excalidraw file
  const filePath = path.resolve(__dirname, '../../docs/images/finclaw-architecture.excalidraw');
  const fileContent = fs.readFileSync(filePath, 'utf-8');
  
  // Import via Excalidraw's API
  await page.evaluate(async (content) => {
    // Excalidraw stores state in localStorage and has an import mechanism
    const data = JSON.parse(content);
    // Use the window.excalidrawAPI if available
    if (window.excalidrawAPI) {
      await window.excalidrawAPI.updateScene({
        elements: data.elements,
        appState: { ...data.appState, theme: 'dark' }
      });
    }
  }, fileContent);
  
  await page.waitForTimeout(2000);
  
  // Take a screenshot of the canvas area
  const canvas = await page.locator('canvas').first();
  await canvas.screenshot({ 
    path: path.resolve(__dirname, '../../docs/images/hero.png'),
    type: 'png'
  });
  
  console.log('Exported to docs/images/hero.png');
  await browser.close();
})();
