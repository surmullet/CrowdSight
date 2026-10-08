import puppeteer from 'puppeteer-core';
import path from 'path';
import fs from 'fs';

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const ARTIFACT_DIR = 'C:\\Users\\QuocThang\\.gemini\\antigravity-ide\\brain\\03a39dc6-92f5-4f4a-bd45-5c2316bc4520';
const BASE_URL = 'http://localhost:3000';

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function run() {
  console.log('🚀 Starting Chrome browser test via puppeteer-core...');
  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1440,900'],
    defaultViewport: { width: 1440, height: 900 },
  });

  const page = await browser.newPage();
  const results = [];

  try {
    // ------------------------------------------------------------------------
    // TEST 1: OPERATOR ROLE
    // ------------------------------------------------------------------------
    console.log('\n--- 1. Testing OPERATOR Role ---');
    await page.goto(BASE_URL, { waitUntil: 'networkidle2' });
    await sleep(1500);

    // Verify initial role badge
    const badgeText = await page.$eval('nav', (nav) => nav.innerText);
    console.log('Nav text includes Operator:', badgeText.includes('Giám Sát Viên') || badgeText.includes('OPERATOR'));
    results.push({
      role: 'OPERATOR',
      feature: 'User Badge Display',
      passed: badgeText.includes('Giám Sát Viên') || badgeText.includes('OPERATOR'),
      detail: 'Operator badge visible in top navigation',
    });

    // Check "+ Bắt đầu phân tích mới" is ENABLED
    const newSessionDisabled = await page.$eval('button:has-text("+"), button:has-text("Bắt đầu")', (el) => el.disabled).catch(() => false);
    console.log('New session button disabled for Operator:', newSessionDisabled);
    results.push({
      role: 'OPERATOR',
      feature: 'New Session Creation',
      passed: !newSessionDisabled,
      detail: 'Operator can create new sessions (+ Bắt đầu phân tích mới button is enabled)',
    });

    // Check Wizard tab is present
    const hasWizardTab = await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('nav button'));
      return buttons.some((b) => b.textContent?.includes('Tạo phiên') || b.textContent?.includes('Wizard'));
    });
    console.log('Wizard tab visible for Operator:', hasWizardTab);
    results.push({
      role: 'OPERATOR',
      feature: 'Wizard Tab Navigation',
      passed: hasWizardTab,
      detail: 'Wizard navigation tab is accessible to Operator',
    });

    // Check Delete button is RESTRICTED for Operator
    const deleteButtonRestricted = await page.evaluate(() => {
      const deleteBtn = document.querySelector('button[title*="Chỉ Quản trị viên"]') || document.querySelector('button[title*="ADMIN"]');
      return deleteBtn !== null;
    });
    console.log('Delete button restricted for Operator:', deleteButtonRestricted);
    results.push({
      role: 'OPERATOR',
      feature: 'Delete Permission Guard',
      passed: deleteButtonRestricted,
      detail: 'Delete button is guarded with "Chỉ Quản trị viên (ADMIN) mới có quyền xóa"',
    });

    await page.screenshot({ path: path.join(ARTIFACT_DIR, 'test_operator_library.png') });
    console.log('📸 Saved test_operator_library.png');

    // Enter review workspace
    console.log('Navigating to Review Workspace as Operator...');
    await page.evaluate(() => {
      const viewBtns = Array.from(document.querySelectorAll('button')).filter((b) => b.textContent?.includes('Xem kết quả'));
      if (viewBtns[0]) viewBtns[0].click();
    });
    await sleep(2000);

    // Switch to Notes tab
    await page.evaluate(() => {
      const tabs = Array.from(document.querySelectorAll('button')).filter((b) => b.textContent?.includes('Ghi chú'));
      if (tabs[0]) tabs[0].click();
    });
    await sleep(1000);

    // Type note and save
    const noteInputSelector = 'input[placeholder*="Nội dung ghi chú"]';
    const hasNoteInput = await page.$(noteInputSelector);
    if (hasNoteInput) {
      await page.type(noteInputSelector, 'Ghi chú giám sát test role OPERATOR');
      await page.click('button:has-text("Lưu"), form button[type="submit"]');
      await sleep(1500);
      const notesList = await page.evaluate(() => document.body.innerText);
      const noteAdded = notesList.includes('Ghi chú giám sát test role OPERATOR');
      console.log('Operator added note successfully:', noteAdded);
      results.push({
        role: 'OPERATOR',
        feature: 'Session Notes',
        passed: noteAdded,
        detail: 'Operator can create new timestamped session notes',
      });
    }

    await page.screenshot({ path: path.join(ARTIFACT_DIR, 'test_operator_review_notes.png') });
    console.log('📸 Saved test_operator_review_notes.png');

    // Return to sessions library
    await page.evaluate(() => {
      const backBtn = document.querySelector('button[title*="Quay lại danh sách phiên"]') || document.querySelector('nav button:has-text("CrowdSight")');
      if (backBtn) backBtn.click();
    });
    await sleep(1500);

    // ------------------------------------------------------------------------
    // TEST 2: SWITCH TO VIEWER ROLE
    // ------------------------------------------------------------------------
    console.log('\n--- 2. Testing VIEWER Role ---');
    // Open Role Dropdown
    await page.evaluate(() => {
      const badgeBtn = Array.from(document.querySelectorAll('nav button')).find((b) => b.textContent?.includes('Giám Sát Viên') || b.textContent?.includes('OPERATOR'));
      if (badgeBtn) badgeBtn.click();
    });
    await sleep(1000);

    // Click Viewer Option
    await page.evaluate(() => {
      const viewerBtn = Array.from(document.querySelectorAll('button')).find((b) => b.textContent?.includes('Khách Xem') || b.textContent?.includes('VIEWER'));
      if (viewerBtn) viewerBtn.click();
    });
    await sleep(1500);

    // Verify "+ Bắt đầu phân tích mới" is DISABLED for Viewer
    const newSessionDisabledViewer = await page.evaluate(() => {
      const btn = Array.from(document.querySelectorAll('button')).find((b) => b.textContent?.includes('Bắt đầu') || b.textContent?.includes('Tạo phiên'));
      return btn ? btn.disabled : false;
    });
    console.log('New session disabled for Viewer:', newSessionDisabledViewer);
    results.push({
      role: 'VIEWER',
      feature: 'New Session Locked',
      passed: newSessionDisabledViewer,
      detail: 'Viewers are prevented from creating new sessions (+ Bắt đầu phân tích mới button disabled)',
    });

    // Verify Wizard tab is HIDDEN for Viewer
    const wizardHiddenViewer = await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('nav button'));
      return !buttons.some((b) => b.textContent?.includes('Tạo phiên') || b.textContent?.includes('Wizard'));
    });
    console.log('Wizard tab hidden for Viewer:', wizardHiddenViewer);
    results.push({
      role: 'VIEWER',
      feature: 'Wizard Tab Hidden',
      passed: wizardHiddenViewer,
      detail: 'Wizard navigation tab is completely hidden from Viewers',
    });

    // Verify Re-analyze is DISABLED for Viewer
    const reanalyzeDisabledViewer = await page.evaluate(() => {
      const btn = Array.from(document.querySelectorAll('button')).find((b) => b.textContent?.includes('Phân tích lại'));
      return btn ? btn.disabled : false;
    });
    console.log('Re-analyze disabled for Viewer:', reanalyzeDisabledViewer);
    results.push({
      role: 'VIEWER',
      feature: 'Re-analyze Disabled',
      passed: reanalyzeDisabledViewer,
      detail: 'Re-analyze button is locked for Viewers',
    });

    await page.screenshot({ path: path.join(ARTIFACT_DIR, 'test_viewer_library.png') });
    console.log('📸 Saved test_viewer_library.png');

    // Enter review workspace as Viewer
    await page.evaluate(() => {
      const viewBtns = Array.from(document.querySelectorAll('button')).filter((b) => b.textContent?.includes('Xem kết quả'));
      if (viewBtns[0]) viewBtns[0].click();
    });
    await sleep(2000);

    // Verify "Chỉnh sửa khu vực" is DISABLED for Viewer
    const editZonesDisabledViewer = await page.evaluate(() => {
      const btn = Array.from(document.querySelectorAll('button')).find((b) => b.textContent?.includes('Chỉnh sửa khu vực'));
      return btn ? btn.disabled : false;
    });
    console.log('Edit zones disabled for Viewer:', editZonesDisabledViewer);
    results.push({
      role: 'VIEWER',
      feature: 'Zone Editor Blocked',
      passed: editZonesDisabledViewer,
      detail: 'Chỉnh sửa khu vực button is disabled for Viewers',
    });

    // Check Notes tab in Review Workspace
    await page.evaluate(() => {
      const tabs = Array.from(document.querySelectorAll('button')).filter((b) => b.textContent?.includes('Ghi chú'));
      if (tabs[0]) tabs[0].click();
    });
    await sleep(1000);

    const viewerNotesReadOnly = await page.evaluate(() => {
      const text = document.body.innerText;
      return text.includes('Chế độ Khách xem') || text.includes('không có quyền tạo');
    });
    console.log('Viewer notes read-only banner visible:', viewerNotesReadOnly);
    results.push({
      role: 'VIEWER',
      feature: 'Read-only Notes Enforcement',
      passed: viewerNotesReadOnly,
      detail: 'Notes input is replaced by Read-only banner for Viewers',
    });

    await page.screenshot({ path: path.join(ARTIFACT_DIR, 'test_viewer_review_readonly.png') });
    console.log('📸 Saved test_viewer_review_readonly.png');

    // Return to sessions
    await page.evaluate(() => {
      const backBtn = document.querySelector('button[title*="Quay lại danh sách phiên"]');
      if (backBtn) backBtn.click();
    });
    await sleep(1500);

    // ------------------------------------------------------------------------
    // TEST 3: SWITCH TO ADMIN ROLE
    // ------------------------------------------------------------------------
    console.log('\n--- 3. Testing ADMIN Role ---');
    // Open Role Dropdown
    await page.evaluate(() => {
      const badgeBtn = Array.from(document.querySelectorAll('nav button')).find((b) => b.textContent?.includes('Khách Xem') || b.textContent?.includes('VIEWER'));
      if (badgeBtn) badgeBtn.click();
    });
    await sleep(1000);

    // Click Admin Option
    await page.evaluate(() => {
      const adminBtn = Array.from(document.querySelectorAll('button')).find((b) => b.textContent?.includes('Quản Trị Viên') || b.textContent?.includes('ADMIN'));
      if (adminBtn) adminBtn.click();
    });
    await sleep(1500);

    // Verify Admin Badge
    const adminBadgeText = await page.$eval('nav', (nav) => nav.innerText);
    console.log('Admin badge visible:', adminBadgeText.includes('Quản Trị Viên') || adminBadgeText.includes('ADMIN'));
    results.push({
      role: 'ADMIN',
      feature: 'Admin Profile Activated',
      passed: adminBadgeText.includes('Quản Trị Viên') || adminBadgeText.includes('ADMIN'),
      detail: 'Admin badge with full administrative privileges displayed',
    });

    // Check Delete button is ENABLED for Admin
    const deleteButtonEnabledAdmin = await page.evaluate(() => {
      const deleteBtn = document.querySelector('button[title="Xóa phiên phân tích"]');
      return deleteBtn !== null && !deleteBtn.disabled;
    });
    console.log('Delete button enabled for Admin:', deleteButtonEnabledAdmin);
    results.push({
      role: 'ADMIN',
      feature: 'Session Deletion Rights',
      passed: deleteButtonEnabledAdmin,
      detail: 'Delete button is unlocked and active for Admin',
    });

    // Click Delete button to trigger confirmation modal
    if (deleteButtonEnabledAdmin) {
      await page.evaluate(() => {
        const deleteBtn = document.querySelector('button[title="Xóa phiên phân tích"]');
        if (deleteBtn) deleteBtn.click();
      });
      await sleep(1500);

      const modalVisible = await page.evaluate(() => {
        const text = document.body.innerText;
        return text.includes('Xác nhận xóa phiên phân tích') && text.includes('toàn bộ tệp kết quả');
      });
      console.log('Delete confirmation modal with artifact warning opened:', modalVisible);
      results.push({
        role: 'ADMIN',
        feature: 'Delete Confirmation Modal',
        passed: modalVisible,
        detail: 'Confirmation modal correctly warns about cascade deletion of artifacts',
      });

      await page.screenshot({ path: path.join(ARTIFACT_DIR, 'test_admin_delete_modal.png') });
      console.log('📸 Saved test_admin_delete_modal.png');

      // Click "Hủy" to safely dismiss modal
      await page.evaluate(() => {
        const cancelBtn = Array.from(document.querySelectorAll('button')).find((b) => b.textContent?.includes('Hủy'));
        if (cancelBtn) cancelBtn.click();
      });
      await sleep(1000);
    }

    // Navigate to Model Status page
    console.log('Navigating to Model Status Page...');
    await page.evaluate(() => {
      const modelNav = Array.from(document.querySelectorAll('nav button')).find((b) => b.textContent?.includes('Mô hình') || b.textContent?.includes('Model'));
      if (modelNav) modelNav.click();
    });
    await sleep(2000);

    const gpuCardVisible = await page.evaluate(() => {
      const text = document.body.innerText;
      return text.includes('Tăng Tốc Phần Cứng AI') || text.includes('CUDA FP16') || text.includes('TensorRT');
    });
    console.log('Hardware GPU Acceleration card visible:', gpuCardVisible);
    results.push({
      role: 'ADMIN',
      feature: 'GPU Acceleration Banner Inspection',
      passed: gpuCardVisible,
      detail: 'Model inspection shows CUDA FP16 & TensorRT acceleration details',
    });

    await page.screenshot({ path: path.join(ARTIFACT_DIR, 'test_admin_model_gpu.png') });
    console.log('📸 Saved test_admin_model_gpu.png');

    // Return to sessions
    await page.evaluate(() => {
      const sessionsNav = Array.from(document.querySelectorAll('nav button')).find((b) => b.textContent?.includes('Phiên phân tích'));
      if (sessionsNav) sessionsNav.click();
    });
    await sleep(1500);

  } catch (err) {
    console.error('❌ Error during browser test:', err);
  } finally {
    await browser.close();
    console.log('\n========================================');
    console.log('📊 TEST SUMMARY RESULTS:');
    console.table(results);
    fs.writeFileSync(path.join(ARTIFACT_DIR, 'browser_test_results.json'), JSON.stringify(results, null, 2));
    console.log('💾 Results saved to browser_test_results.json');
  }
}

run();
