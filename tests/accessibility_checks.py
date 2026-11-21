"""Behaviour checks complement axe: actual focus, keyboard, spacing and dialogs."""
from playwright.sync_api import expect

SPACING = """* { line-height: 1.5 !important; letter-spacing: .12em !important;
    word-spacing: .16em !important; } p { margin-bottom: 2em !important; }"""


def visit(page, origin, route):
    page.goto(origin + route)
    page.wait_for_load_state('networkidle')


def check_keyboard_and_reflow(public, student, admin, origin):
    # Skip links must move keyboard focus beyond repeated navigation on every shell.
    for page, route in ((public, '/'), (student, '/dashboard'), (admin, '/admin/users')):
        visit(page, origin, route)
        page.locator('.skip-link').focus()
        page.keyboard.press('Enter')
        assert page.evaluate("document.querySelector('main').contains(document.activeElement)")
        assert page.evaluate("document.activeElement.matches('main,.admin-content')")

    visit(public, origin, '/')
    public.locator('#moduleTab0').focus()
    public.keyboard.press('ArrowRight')
    expect(public.locator('#moduleTab1')).to_be_focused()
    expect(public.locator('#modulePanel1')).to_be_visible()
    public.keyboard.press('End')
    expect(public.locator('#moduleTab2')).to_be_focused()

    # An authentication error remains readable and accepts password manager/paste.
    visit(public, origin, '/login')
    public.locator('#loginIdentifier').fill('admin')
    public.locator('#loginPassword').fill('incorrect-password')
    public.locator('#loginPassword').press('Enter')
    expect(public.locator('#authErrorMsg')).to_be_focused()
    expect(public.locator('#authErrorMsg')).not_to_be_empty()
    public.get_by_role('button', name='Lupa kata sandi?').click()
    public.keyboard.press('Escape')
    expect(public.get_by_role('button', name='Lupa kata sandi?')).to_be_focused()

    # Keyboard combobox navigation commits on Enter, not on exploration or Escape.
    visit(admin, origin, '/admin/users')
    combo = admin.locator('#userRoleFilter-combo')
    combo.focus()
    before = admin.locator('#userRoleFilter').input_value()
    combo.press('ArrowUp')
    expect(combo).to_have_attribute('aria-activedescendant', 'userRoleFilter-combo-list-2')
    combo.press('Escape')
    assert admin.locator('#userRoleFilter').input_value() == before
    expect(combo).to_have_attribute('aria-expanded', 'false')
    combo.press('ArrowDown')
    combo.press('ArrowDown')
    combo.press('Enter')
    assert admin.locator('#userRoleFilter').input_value() == 'admin'
    expect(combo).to_be_focused()
    combo.fill('Semua')
    combo.press('ArrowDown')
    combo.press('Enter')
    assert admin.locator('#userRoleFilter').input_value() == ''

    # Pointer cancellation: pressing then releasing outside an option must not commit.
    combo.click()
    option = admin.locator('#userRoleFilter-combo-list-1')
    box = option.bounding_box()
    admin.mouse.move(box['x'] + 5, box['y'] + 5)
    admin.mouse.down()
    admin.mouse.move(1, 1)
    admin.mouse.up()
    assert admin.locator('#userRoleFilter').input_value() == ''
    combo.press('Escape')

    admin.locator('#adminUserDropdownToggle').click()
    admin.keyboard.press('Tab')
    assert admin.evaluate("document.activeElement.closest('#adminUserDropdown') !== null")
    admin.keyboard.press('Escape')
    expect(admin.locator('#adminUserDropdownToggle')).to_be_focused()

    # 320 CSS px represents reflow at 400% on a 1280px-wide desktop viewport.
    admin.set_viewport_size({'width': 320, 'height': 480})
    admin.locator('#adminSidebarToggle').click()
    expect(admin.locator('.admin-drawer-close')).to_be_focused()
    for _ in range(14):
        admin.keyboard.press('Tab')
        assert admin.evaluate("document.activeElement.closest('#adminSidebar') !== null")
    admin.keyboard.press('Escape')
    expect(admin.locator('#adminSidebarToggle')).to_be_focused()
    admin.locator('#adminSidebarToggle').click()
    admin.locator('#subtabQuestions').click()
    expect(admin.locator('#adminPageTitle')).to_be_focused()
    expect(admin.locator('#adminPageTitle')).to_have_text('Bank soal')
    expect(admin.locator('#subtabQuestions')).to_have_attribute('aria-current', 'page')
    add_question = admin.get_by_role('button', name='Tambah soal', exact=True)
    assert add_question.bounding_box()['height'] < 80, 'Do not split action labels mid-word'

    # Dialog must keep its save action reachable in a short viewport with text spacing.
    visit(admin, origin, '/admin/users')
    opener = admin.get_by_role('button', name='Tambah akun', exact=True)
    opener.click()
    field = admin.locator('#editUserName')
    assert field.evaluate("el => getComputedStyle(el).outlineWidth") == '3px'
    assert field.evaluate("el => getComputedStyle(el).borderColor") == 'rgb(100, 116, 139)'
    admin.add_style_tag(content=SPACING)
    save = admin.locator('#saveUserButton')
    save.focus()
    expect(save).to_be_in_viewport()
    assert save.evaluate("el => { const r = el.getBoundingClientRect(); return r.right <= innerWidth && r.left >= 0; }")
    admin.keyboard.press('Escape')
    expect(opener).to_be_focused()

    for page, route in ((public, '/register'), (student, '/practice?module=reading'),
                        (student, '/exam'), (admin, '/admin/packages'), (admin, '/admin/questions')):
        page.set_viewport_size({'width': 320, 'height': 812})
        visit(page, origin, route)
        page.add_style_tag(content=SPACING)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), route
        assert page.evaluate("""() => [...document.querySelectorAll('button,input,select,textarea')]
          .filter(el => el.getClientRects().length && !el.closest('[inert]'))
          .every(el => { const r = el.getBoundingClientRect(); return r.left >= -1 && r.right <= innerWidth + 1; })"""), route

    # Text enlargement as well as reflow, reduced motion and Windows forced colours.
    visit(public, origin, '/login')
    public.add_style_tag(content='html { font-size: 200%; }')
    assert public.evaluate('document.documentElement.scrollWidth <= innerWidth')
    public.locator('#loginIdentifier').focus()
    public.keyboard.press('Tab')
    expect(public.get_by_role('button', name='Lupa kata sandi?')).to_be_focused()
    public.emulate_media(forced_colors='active', reduced_motion='reduce')
    assert public.locator(':focus-visible').evaluate("el => getComputedStyle(el).outlineStyle") != 'none'
    assert public.locator(':focus-visible').evaluate("el => getComputedStyle(el).transitionDuration") == '0s'
    public.emulate_media(forced_colors='none')
    public.route('**/pages/privacy.html', lambda route: route.abort())
    visit(public, origin, '/privacy')
    expect(public.locator('main')).to_be_focused()
    expect(public.get_by_role('alert')).to_contain_text('Data belum dapat dimuat')
    public.unroute('**/pages/privacy.html')
    public.get_by_role('button', name='Coba lagi', exact=True).click()
    expect(public.locator('h1')).to_contain_text('Privasi')
    print('PASS: skip links, tabs, auth errors, combobox commit/cancel, drawer focus, dialog scroll, 320px reflow, spacing, text enlargement and forced colours', flush=True)
