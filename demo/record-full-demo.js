/**
 * CSNavigator FAST Demo - 30-40 seconds
 */

const { chromium } = require('playwright');
const path = require('path');

const CONFIG = {
  baseUrl: 'http://18.214.136.155:3000',
  credentials: { email: 'admin@test.com', password: 'admin' },
  files: {
    degreeWorks: '/Users/theaayushstha/Desktop/MyDegreeWorks.pdf',
    profilePicture: '/Users/theaayushstha/Desktop/profile.jpg'
  },
};

async function fastDemo() {
  console.log('🎬 FAST Demo Starting...\n');

  const browser = await chromium.launch({
    headless: false,
    args: ['--start-maximized', '--window-size=1920,1080'],
  });

  const context = await browser.newContext({ viewport: null });
  const page = await context.newPage();

  try {
    // Set zoom to 67%
    await page.goto(CONFIG.baseUrl);
    await page.evaluate(() => document.body.style.zoom = '0.67');
    await page.waitForTimeout(800);

    // PART 1: Try Chat - Quick question
    console.log('1. Try Chat');
    await page.click('text=Try CSNavigator').catch(() => page.click('button:has-text("Try")').catch(() => {}));
    await page.waitForTimeout(600);

    // Type fast and send
    const input = page.locator('input[placeholder*="message"], textarea, input[type="text"]').first();
    await input.fill('Who is the chair of Computer Science department?');
    await page.mouse.move(700, 400);
    await page.keyboard.press('Enter');
    await page.waitForTimeout(2500); // Brief wait for response

    // PART 2: Login
    console.log('2. Login');
    await page.click('text=Sign In').catch(() => page.click('text=Login').catch(() => {}));
    await page.waitForTimeout(500);

    await page.locator('input[type="email"], input[name="email"]').first().fill(CONFIG.credentials.email);
    await page.locator('input[type="password"]').first().fill(CONFIG.credentials.password);
    await page.mouse.move(600, 500);
    await page.click('button[type="submit"]').catch(() => page.click('button:has-text("Login")').catch(() => {}));
    await page.waitForTimeout(1500);

    // PART 3: New Chat
    console.log('3. New Chat');
    await page.click('text=New Chat').catch(() => {});
    await page.waitForTimeout(500);

    const chatInput = page.locator('input[placeholder*="message"], textarea').first();
    await chatInput.fill('What are the CS degree requirements?');
    await page.mouse.move(800, 350);
    await page.keyboard.press('Enter');
    await page.waitForTimeout(2000);

    // PART 4: Upload DegreeWorks
    console.log('4. Upload DegreeWorks');
    await page.click('text=Curriculum').catch(() => page.click('text=Upload').catch(() => {}));
    await page.waitForTimeout(500);

    const fileInput = page.locator('input[type="file"]').first();
    if (await fileInput.count() > 0) {
      await fileInput.setInputFiles(CONFIG.files.degreeWorks);
      await page.mouse.move(500, 400);
      await page.waitForTimeout(1000);
      await page.click('button:has-text("Upload")').catch(() => {});
      await page.waitForTimeout(800);
    }

    // PART 5: Curriculum page scroll
    console.log('5. Curriculum');
    await page.mouse.move(640, 500);
    await page.mouse.wheel(0, 200);
    await page.waitForTimeout(400);
    await page.mouse.wheel(0, -200);
    await page.waitForTimeout(400);

    // PART 6: Dark Mode
    console.log('6. Dark Mode');
    const darkToggle = page.locator('button[aria-label*="theme"], button[aria-label*="dark"], [class*="theme"], button:has(svg)').first();
    await darkToggle.click().catch(() => {});
    await page.mouse.move(900, 100);
    await page.waitForTimeout(600);
    await darkToggle.click().catch(() => {}); // Toggle back
    await page.waitForTimeout(400);

    // PART 7: Delete Chat
    console.log('7. Delete Feature');
    await page.click('text=Chat').catch(() => {});
    await page.waitForTimeout(400);
    const deleteBtn = page.locator('[class*="delete"], button:has([class*="trash"]), button[aria-label*="delete"]').first();
    await deleteBtn.click().catch(() => {});
    await page.mouse.move(640, 400);
    await page.waitForTimeout(500);
    await page.click('text=Cancel').catch(() => page.keyboard.press('Escape').catch(() => {}));
    await page.waitForTimeout(300);

    // PART 8: Profile Update
    console.log('8. Profile');
    await page.click('text=Profile').catch(() => page.click('[class*="profile"]').catch(() => {}));
    await page.waitForTimeout(500);

    await page.click('text=Update').catch(() => page.click('text=Edit').catch(() => {}));
    await page.waitForTimeout(400);

    const profileInput = page.locator('input[type="file"]').first();
    if (await profileInput.count() > 0) {
      await profileInput.setInputFiles(CONFIG.files.profilePicture);
      await page.mouse.move(700, 450);
      await page.waitForTimeout(600);
      await page.click('button:has-text("Save")').catch(() => page.click('button:has-text("Update")').catch(() => {}));
      await page.waitForTimeout(500);
    }

    // Final: Back to landing
    console.log('9. Done!');
    await page.goto(CONFIG.baseUrl);
    await page.evaluate(() => document.body.style.zoom = '0.67');
    await page.mouse.move(640, 400);
    await page.waitForTimeout(1000);

    console.log('\n✅ Fast demo complete!');

  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await page.waitForTimeout(2000); // Brief pause at end
    await context.close();
    await browser.close();
  }
}

fastDemo().catch(console.error);
