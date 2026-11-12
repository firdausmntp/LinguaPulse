"""CRUD account boundaries and responsive admin navigation, on the temporary fixture."""
from playwright.sync_api import expect


def check_user_api(request):
    payload = {'mode': 'create', 'display_name': 'Account CRUD', 'username': 'crud_api',
               'email': 'crud@example.test', 'role': 'student', 'password': 'accountpass123'}
    status, created = request('/api/admin/users', payload)
    assert status == 200, created
    user_id = created['user']['user_id']
    assert 'password_hash' not in created['user']
    assert request('/api/admin/users', payload)[0] == 400
    update = {**payload, 'mode': 'update', 'user_id': user_id, 'display_name': 'Updated account', 'password': ''}
    assert request('/api/admin/users', update)[0] == 200
    admin = request('/api/auth/me')[1]['user']
    assert request('/api/admin/users?id=' + str(admin['user_id']), method='DELETE')[0] == 400
    assert request('/api/admin/users', {**update, 'user_id': admin['user_id'], 'username': admin['username'], 'email': admin['email']})[0] == 400
    from urllib.request import build_opener, ProxyHandler, HTTPCookieProcessor
    from http.cookiejar import CookieJar
    client = build_opener(ProxyHandler({}), HTTPCookieProcessor(CookieJar()))
    assert request('/api/auth/login', {'identifier': 'crud_api', 'password': 'accountpass123'}, opener=client)[0] == 200
    assert request('/api/admin/users', payload, opener=client)[0] == 403
    assert request('/api/admin/users', {**update, 'password': 'newpassword123'})[0] == 200
    assert request('/api/history', opener=client)[0] == 401
    assert request('/api/admin/users?id=' + str(user_id), method='DELETE')[0] == 200
    assert request('/api/auth/login', {'identifier': 'crud_api', 'password': 'newpassword123'}, opener=client)[0] == 401
    print('PASS: account CRUD, duplicate validation, self-protection, role access and session revocation', flush=True)


def check_user_browser(page, origin, artifacts):
    page.goto(origin + '/admin?tab=users')
    page.wait_for_load_state('networkidle')
    expect(page.locator('#adminUsersBody')).to_contain_text('admin')
    toggle = page.locator('#adminSidebarToggle')
    toggle.click()
    expect(page.locator('body')).to_have_class(__import__('re').compile('admin-collapsed'))
    page.reload()
    page.wait_for_load_state('networkidle')
    expect(page.locator('body')).to_have_class(__import__('re').compile('admin-collapsed'))
    page.locator('#adminSidebarToggle').click()
    page.get_by_role('button', name='Tambah akun', exact=True).click()
    expect(page.locator('#userEditorDialog')).to_be_visible()
    page.locator('#editUserName').fill('UI Account')
    page.locator('#editUserUsername').fill('crud_ui')
    page.locator('#editUserEmail').fill('ui@example.test')
    page.locator('#editUserPassword').fill('uipassword123')
    page.locator('#saveUserButton').click()
    expect(page.locator('#userListStatus')).to_contain_text('tersimpan')
    page.locator('#userSearch').fill('crud_ui')
    expect(page.locator('#adminUsersBody tr')).to_have_count(1)
    page.locator('#adminUsersBody').get_by_role('button', name='Edit', exact=True).click()
    page.locator('#editUserName').fill('UI Account Updated')
    page.locator('#saveUserButton').click()
    expect(page.locator('#adminUsersBody')).to_contain_text('UI Account Updated')
    page.locator('#userSearch').fill('')
    page.screenshot(path=str(artifacts / 'users-dashboard-desktop.png'), full_page=True)
    for width in (375, 320):
        page.set_viewport_size({'width': width, 'height': 812})
        page.reload()
        page.wait_for_load_state('networkidle')
        expect(page.locator('#adminSidebarToggle')).to_have_attribute('aria-expanded', 'false')
        page.locator('#adminSidebarToggle').click()
        expect(page.locator('#adminSidebarToggle')).to_have_attribute('aria-expanded', 'true')
        page.keyboard.press('Escape')
        expect(page.locator('#adminSidebarToggle')).to_have_attribute('aria-expanded', 'false')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert page.locator('.users-table').evaluate('(table) => table.scrollWidth <= table.clientWidth + 1')
        assert page.locator('.user-cell').evaluate_all('(cells) => cells.every(cell => cell.scrollWidth <= cell.clientWidth + 1)')
        page.screenshot(path=str(artifacts / f'users-dashboard-{width}.png'), full_page=True)
    page.set_viewport_size({'width': 1440, 'height': 900})
    page.locator('#userSearch').fill('crud_ui')
    page.locator('#adminUsersBody').get_by_role('button', name='Hapus', exact=True).click()
    expect(page.locator('#adminConfirmDialog')).to_be_visible()
    page.locator('#adminConfirmAccept').click()
    expect(page.locator('#userListStatus')).to_contain_text('dihapus')
    expect(page.locator('#adminUsersBody')).not_to_contain_text('UI Account Updated')
    print('PASS: account editor/delete, sidebar persistence, mobile drawer/Escape and 320/375px layout', flush=True)
