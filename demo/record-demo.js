/**
 * CSNavigator Demo Recording Script
 *
 * This script automates the browser and records a demo video.
 *
 * Usage:
 *   cd demo
 *   npm install
 *   npm run install-browsers
 *   npm run record
 *
 * Output: demo-recording.webm
 */

const { chromium } = require('playwright');
const path = require('path');

// Configuration
const CONFIG = {
  baseUrl: 'http://18.214.136.155:3000', // Deployed URL
  // baseUrl: 'http://localhost:5173', // Local development
  outputPath: path.join(__dirname, 'demo-recording.webm'),
  viewport: { width: 1280, height: 720 },
  slowMo: 50, // Slow down actions for smoother recording
};

// Helper: Type text with realistic speed
async function typeSlowly(page, selector, text, delay = 80) {
  await page.click(selector);
  for (const char of text) {
    await page.keyboard.type(char, { delay });
  }
}

// Helper: Wait and pause for viewer
async function pause(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Main demo flow
async function recordDemo() {
  console.log('🎬 Starting CSNavigator Demo Recording...\n');

  const browser = await chromium.launch({
    headless: false, // Show browser for debugging (set true for CI)
    slowMo: CONFIG.slowMo,
  });

  const context = await browser.newContext({
    viewport: CONFIG.viewport,
    recordVideo: {
      dir: __dirname,
      size: CONFIG.viewport,
    },
  });

  const page = await context.newPage();

  try {
    // ========== SCENE 1: Landing Page ==========
    console.log('📍 Scene 1: Landing Page');
    await page.goto(CONFIG.baseUrl);
    await pause(3000); // Let viewers see the landing page

    // Scroll down slightly to show content
    await page.mouse.wheel(0, 300);
    await pause(2000);

    // Scroll back up
    await page.mouse.wheel(0, -300);
    await pause(1000);

    // ========== SCENE 2: Try Chat Feature ==========
    console.log('📍 Scene 2: Opening Try Chat');

    // Find and click the "Try CSNavigator" or similar button
    const tryButton = await page.locator('text=/Try|Get Started|Chat Now/i').first();
    if (await tryButton.isVisible()) {
      await tryButton.click();
      await pause(2000);
    } else {
      // Fallback: look for any prominent CTA button
      await page.click('button:has-text("Try"), a:has-text("Try"), button:has-text("Start")');
      await pause(2000);
    }

    // ========== SCENE 3: First Question ==========
    console.log('📍 Scene 3: Asking first question');

    // Wait for chat input to be visible
    await page.waitForSelector('input[type="text"], textarea', { timeout: 10000 });
    await pause(1000);

    // Type first question
    const chatInput = await page.locator('input[type="text"], textarea').first();
    await typeSlowly(page, 'input[type="text"], textarea', 'What courses do I need for a Computer Science degree?');
    await pause(500);

    // Submit the question
    await page.keyboard.press('Enter');
    await pause(5000); // Wait for AI response

    // ========== SCENE 4: Second Question ==========
    console.log('📍 Scene 4: Asking second question');

    await typeSlowly(page, 'input[type="text"], textarea', 'Who is the chair of the CS department?');
    await page.keyboard.press('Enter');
    await pause(5000);

    // ========== SCENE 5: Third Question ==========
    console.log('📍 Scene 5: Asking third question');

    await typeSlowly(page, 'input[type="text"], textarea', 'What career opportunities are available after graduation?');
    await page.keyboard.press('Enter');
    await pause(5000);

    // ========== SCENE 6: Show Session Timer ==========
    console.log('📍 Scene 6: Highlighting session timer');

    // Move mouse to session timer area (top of chat)
    await page.mouse.move(640, 100);
    await pause(2000);

    // ========== SCENE 7: Scroll Through Responses ==========
    console.log('📍 Scene 7: Scrolling through conversation');

    // Scroll up to see all responses
    const chatContainer = await page.locator('.chat-messages, .messages-container, [class*="message"]').first();
    if (await chatContainer.isVisible()) {
      await chatContainer.evaluate(el => el.scrollTop = 0);
      await pause(1000);
      await chatContainer.evaluate(el => el.scrollTop = el.scrollHeight);
      await pause(2000);
    }

    // ========== SCENE 8: Close and Show Login ==========
    console.log('📍 Scene 8: Showing login option');

    // Look for close button or navigate to login
    const closeBtn = await page.locator('[class*="close"], button:has-text("Close"), .modal-close').first();
    if (await closeBtn.isVisible()) {
      await closeBtn.click();
      await pause(1500);
    }

    // Click Sign In / Login
    const loginLink = await page.locator('text=/Sign In|Login|Log In/i').first();
    if (await loginLink.isVisible()) {
      await loginLink.click();
      await pause(2000);
    }

    // ========== SCENE 9: Final Landing Shot ==========
    console.log('📍 Scene 9: Final shot');

    await page.goto(CONFIG.baseUrl);
    await pause(3000);

    console.log('\n✅ Demo recording complete!');

  } catch (error) {
    console.error('❌ Error during recording:', error.message);
  } finally {
    // Close and save video
    await context.close();
    await browser.close();

    console.log(`\n🎥 Video saved! Check the demo folder for the .webm file`);
    console.log('\n📝 Next steps:');
    console.log('   1. Import the .webm file into Screen Studio or Cap');
    console.log('   2. Add 3D effects and polish');
    console.log('   3. Export as MP4');
  }
}

// Run the demo
recordDemo().catch(console.error);
