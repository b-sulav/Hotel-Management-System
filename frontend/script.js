'use strict';

// Config
const RESORT_CONFIG = {
    API_BASE: '/api',
    WHATSAPP_NUMBER: '9779804262505',
    WHATSAPP_MESSAGE: 'Hi, I have an inquiry!',
};

// Helpers
function extractErrorMessage(data) {
    if (!data)                        return 'An unknown error occurred.';
    if (typeof data.detail === 'string') return data.detail;
    if (Array.isArray(data.detail))   return data.detail.map(err => `${err.loc ? err.loc.join('.') : 'Field'}: ${err.msg}`).join('\n');
    if (data.detail)                  return JSON.stringify(data.detail);
    return 'An unknown error occurred.';
}

async function safeJson(response) {
    try { return await response.json(); } catch { return null; }
}

function initGuestSelect(guestSelectEl) {
    if (!guestSelectEl || guestSelectEl.dataset.initialized === 'true') return;

    const selectId = guestSelectEl.dataset.selectId;
    const selectEl = document.getElementById(selectId);
    const trigger  = guestSelectEl.querySelector('.guest-select-trigger');
    const display  = guestSelectEl.querySelector('.guest-select-display');
    const menu     = guestSelectEl.querySelector('.guest-select-menu');
    const options  = Array.from(guestSelectEl.querySelectorAll('.guest-select-option'));

    if (!selectEl || !trigger || !display || !menu || options.length === 0) return;

    const close = () => {
        menu.classList.add('hidden');
        trigger.setAttribute('aria-expanded', 'false');
    };

    const open = () => {
        document.querySelectorAll('.guest-select').forEach(gs => {
            if (gs !== guestSelectEl) {
                const m = gs.querySelector('.guest-select-menu');
                const t = gs.querySelector('.guest-select-trigger');
                m?.classList.add('hidden');
                t?.setAttribute('aria-expanded', 'false');
            }
        });
        menu.classList.remove('hidden');
        trigger.setAttribute('aria-expanded', 'true');
    };

    const labelForValue = (value) => {
        const match = options.find(o => o.dataset.value === String(value));
        return match ? match.textContent.trim() : '';
    };

    const syncFromSelect = () => {
        const label = labelForValue(selectEl.value) || 'Select guests';
        display.textContent = label;
        options.forEach(o => {
            const selected = o.dataset.value === String(selectEl.value);
            if (selected) o.setAttribute('aria-selected', 'true');
            else o.removeAttribute('aria-selected');
        });
    };

    trigger.addEventListener('click', () => {
        if (menu.classList.contains('hidden')) open();
        else close();
    });

    options.forEach(btn => {
        btn.addEventListener('click', () => {
            selectEl.value = btn.dataset.value;
            selectEl.dispatchEvent(new Event('change', { bubbles: true }));
            close();
        });
    });

    selectEl.addEventListener('change', syncFromSelect);

    guestSelectEl.dataset.initialized = 'true';
    syncFromSelect();
}

document.addEventListener('click', (e) => {
    const gs = e.target.closest('.guest-select');
    if (gs) return;
    document.querySelectorAll('.guest-select').forEach(el => {
        const menu = el.querySelector('.guest-select-menu');
        const trig = el.querySelector('.guest-select-trigger');
        menu?.classList.add('hidden');
        trig?.setAttribute('aria-expanded', 'false');
    });
});

const getNepalDateString = (offsetDays = 0) => {
    const d = new Date();
    d.setDate(d.getDate() + offsetDays);
    return new Intl.DateTimeFormat('en-CA', {
        timeZone: 'Asia/Kathmandu',
        year: 'numeric', month: '2-digit', day: '2-digit',
    }).format(d);
};

const toLocalMidnight = (dateStr) => {
    const [y, m, d] = dateStr.split('-').map(Number);
    return new Date(y, m - 1, d);
};

const fmt = (dateStr) =>
    toLocalMidnight(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

function scrollPanelToTop(panel) {
    if (panel && !panel.classList.contains('hidden')) panel.scrollTop = 0;
}

// WhatsApp float
(function () {
    const link = document.getElementById('whatsappFloatLink');
    if (link) {
        // Overwrite the
        link.href = `https://wa.me/${RESORT_CONFIG.WHATSAPP_NUMBER}?text=${encodeURIComponent(RESORT_CONFIG.WHATSAPP_MESSAGE)}`;
    }
})();

// Navbar
const nav         = document.querySelector('nav');
const menuToggle  = document.querySelector('.menu-toggle');
const navContent  = document.querySelector('.nav-content');
const navLinksArr = document.querySelectorAll('.nav-links a');

menuToggle.addEventListener('click', () => {
    const isActive = navContent.classList.toggle('active');
    menuToggle.classList.toggle('active', isActive);
    menuToggle.setAttribute('aria-expanded', String(isActive));
    nav.style.background = isActive ? 'var(--primary-green)' : '';
    if (isActive) {
        lockBodyScroll();
        document.body.classList.add('menu-open');
        document.documentElement.classList.add('menu-open');
    } else {
        unlockBodyScroll();
        document.body.classList.remove('menu-open');
        document.documentElement.classList.remove('menu-open');
    }
});

navLinksArr.forEach(link => {
    link.addEventListener('click', () => {
        menuToggle.classList.remove('active');
        menuToggle.setAttribute('aria-expanded', 'false');
        navContent.classList.remove('active');
        unlockBodyScroll();
        document.body.classList.remove('menu-open');
        document.documentElement.classList.remove('menu-open');
        if (window.scrollY <= 50) nav.style.background = 'transparent';
    });
});

window.addEventListener('scroll', () => {
    if (window.scrollY > 50 || navContent.classList.contains('active')) {
        nav.classList.add('scrolled');
        nav.style.background = '';
    } else {
        nav.classList.remove('scrolled');
    }
}, { passive: true });

// Scroll-reveal via
(function () {
    const revealEls = document.querySelectorAll('.reveal');
    if (!revealEls.length) return;

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('active');
                observer.unobserve(entry.target); // fire once and stop watching
            }
        });
    }, { threshold: 0, rootMargin: '0px 0px -120px 0px' });

    revealEls.forEach(el => observer.observe(el));
})();

// Gallery carousel
(function () {
    const slides = Array.from(document.querySelectorAll('.carousel-slide'));
    if (!slides.length) return;
    let current = 0;

    const go = (idx) => {
        slides[current].classList.remove('active');
        current = ((idx % slides.length) + slides.length) % slides.length;
        slides[current].classList.add('active');
    };

    document.querySelector('.prev-btn')?.addEventListener('click', () => go(current - 1));
    document.querySelector('.next-btn')?.addEventListener('click', () => go(current + 1));

    setInterval(() => go(current + 1), 5000);
})();

// DOM references
const modal          = document.getElementById('bookingWizardModal');
const step1Panel     = document.getElementById('wizardStep1');
const step2Panel     = document.getElementById('wizardStep2');
const step3Panel     = document.getElementById('wizardStep3');
const wizardBackBtn  = document.getElementById('wizardBackBtn');
const wizardSubtitle = document.getElementById('wizardSubtitle');

// Step 1
const checkinInput        = document.getElementById('checkin');
const checkoutInput       = document.getElementById('checkout');
const dynamicRoomsWrapper = document.getElementById('dynamicRoomsWrapper');
const addRoomOptionBtn    = document.getElementById('addRoomOptionBtn');
const bookingForm         = document.getElementById('bookingForm');
const checkinBtn          = document.getElementById('checkinBtn');
const checkoutBtn         = document.getElementById('checkoutBtn');

// Calendar elements
const calendarEl   = document.getElementById('customCalendar');
const calGrid      = document.getElementById('calGrid');
const calMonthYear = document.getElementById('calMonthYear');
const calPrev      = document.getElementById('calPrev');
const calNext      = document.getElementById('calNext');

// Step 2
const tabsContainer = document.getElementById('roomTabsContainer');
const roomGrid      = document.getElementById('roomGrid');
const proceedBtn    = document.getElementById('proceedBtn');

// Step 3
const guestDetailsForm      = document.getElementById('guestDetailsForm');
const successMessage        = document.getElementById('successMessage');
const closeWizardSuccessBtn = document.getElementById('closeWizardSuccessBtn');

// Wizard state
let currentWizardStep  = 1;
let requestedRooms     = [];
let activeTabId        = null;
let selections         = {};
let liveDatabaseRooms  = [];
let accumulatedRoomCount = 1;

const todayStr = getNepalDateString(0);
const maxCheckinDate = (() => {
    const d = toLocalMidnight(todayStr);
    d.setMonth(d.getMonth() + 1);
    return new Intl.DateTimeFormat('en-CA').format(d);
})();

// Wizard open
document.querySelectorAll('.open-wizard-trigger').forEach(trigger => {
    trigger.addEventListener('click', (e) => {
        e.preventDefault();
        menuToggle?.classList.remove('active');
        menuToggle?.setAttribute('aria-expanded', 'false');
        navContent?.classList.remove('active');
        unlockBodyScroll();
        document.body.classList.remove('menu-open');
        document.documentElement.classList.remove('menu-open');
        openWizard();
    });
});

wizardBackBtn.addEventListener('click', () => {
    if      (currentWizardStep === 1) closeWizard();
    else if (currentWizardStep === 2) transitionToStep(1);
    else if (currentWizardStep === 3) transitionToStep(2);
});

// Close modal
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !modal.classList.contains('hidden')) closeWizard();
});

// Scroll-lock helpers
let _scrollLockY = 0;

function lockBodyScroll() {
    _scrollLockY = window.scrollY;
    document.body.style.position   = 'fixed';
    document.body.style.top        = `-${_scrollLockY}px`;
    document.body.style.left       = '0';
    document.body.style.right      = '0';
    document.body.style.overflow   = 'hidden';
}

function unlockBodyScroll() {
    document.body.style.position   = '';
    document.body.style.top        = '';
    document.body.style.left       = '';
    document.body.style.right      = '';
    document.body.style.overflow   = '';
    window.scrollTo(0, _scrollLockY);
}

function openWizard() {
    modal.classList.remove('hidden');
    lockBodyScroll();
    transitionToStep(1);
    // Focus the
    wizardBackBtn.focus();
}

function closeWizard() {
    modal.classList.add('hidden');
    unlockBodyScroll();
    resetWizardState();
}

function transitionToStep(step) {
    currentWizardStep = step;
    [step1Panel, step2Panel, step3Panel].forEach(p => p.classList.add('hidden'));
    wizardBackBtn.classList.remove('hidden');

    const ind1  = document.getElementById('stepInd1');
    const ind2  = document.getElementById('stepInd2');
    const ind3  = document.getElementById('stepInd3');
    const conn1 = document.getElementById('stepConn1');
    const conn2 = document.getElementById('stepConn2');

    [ind1, ind2, ind3].forEach(el => el?.classList.remove('active', 'done'));
    [conn1, conn2].forEach(el => el?.classList.remove('done'));

    const backSpan = wizardBackBtn.querySelector('span');

    if (step === 1) {
        step1Panel.classList.remove('hidden');
        wizardSubtitle.textContent = 'Reserve Your Stay';
        if (backSpan) backSpan.textContent = 'Close';
        wizardBackBtn.setAttribute('aria-label', 'Close booking wizard');
        ind1?.classList.add('active');
    } else if (step === 2) {
        step2Panel.classList.remove('hidden');
        wizardSubtitle.textContent = 'Select Your Rooms';
        if (backSpan) backSpan.textContent = 'Back';
        wizardBackBtn.setAttribute('aria-label', 'Back to date selection');
        ind1?.classList.add('done');
        conn1?.classList.add('done');
        ind2?.classList.add('active');
        buildRoomTabs();
    } else if (step === 3) {
        step3Panel.classList.remove('hidden');
        wizardSubtitle.textContent = 'Finalize Your Details';
        if (backSpan) backSpan.textContent = 'Back';
        wizardBackBtn.setAttribute('aria-label', 'Back to room selection');
        ind1?.classList.add('done');
        ind2?.classList.add('done');
        conn1?.classList.add('done');
        conn2?.classList.add('done');
        ind3?.classList.add('active');
    }

    [step1Panel, step2Panel, step3Panel].forEach(scrollPanelToTop);
}

function resetWizardState() {
    bookingForm?.reset();
    guestDetailsForm?.reset();

    checkinInput.value  = '';
    checkoutInput.value = '';
    checkinBtn.querySelector('span').textContent  = 'Pick a Date';
    checkoutBtn.querySelector('span').textContent = 'Pick a Date';
    checkinBtn.classList.remove('has-value');
    checkoutBtn.classList.remove('has-value');
    closeCalendar();

    dynamicRoomsWrapper.innerHTML = '';
    accumulatedRoomCount = 1;
    toggleAddRoomButtonVisibility();
    const room1Select = document.getElementById('roomGuests1');
    if (room1Select) room1Select.value = '2';
    document.querySelectorAll('.guest-select').forEach(initGuestSelect);

    guestDetailsForm?.classList.remove('hidden');
    successMessage?.classList.add('hidden');
    selections        = {};
    requestedRooms    = [];
    liveDatabaseRooms = [];
}

// Calendar
let calMode  = null;
let calYear  = 0;
let calMonth = 0;

function openCalendar(mode) {
    calMode = mode;
    const refStr = mode === 'checkin'
        ? (checkinInput.value || todayStr)
        : (checkoutInput.value || checkinInput.value || todayStr);
    const ref = toLocalMidnight(refStr);
    calYear  = ref.getFullYear();
    calMonth = ref.getMonth();
    renderCalendar();

    const btn = mode === 'checkin' ? checkinBtn : checkoutBtn;
    const parent = bookingForm || calendarEl.offsetParent || document.body;
    const rect = btn.getBoundingClientRect();
    const parentRect = parent.getBoundingClientRect();
    const padding = 16;

    let top  = rect.bottom - parentRect.top + 8;
    let left = rect.left   - parentRect.left;

    calendarEl.style.top  = top + 'px';
    calendarEl.style.left = left + 'px';
    calendarEl.classList.remove('hidden');

    const calRect = calendarEl.getBoundingClientRect();

    const maxLeft = parentRect.width - calRect.width - padding;
    left = Math.min(Math.max(left, padding), Math.max(padding, maxLeft));

    if (rect.bottom + calRect.height + 8 > window.innerHeight - padding) {
        top = rect.top - parentRect.top - calRect.height - 8;
        top = Math.max(padding, top);
    }

    calendarEl.style.top  = top + 'px';
    calendarEl.style.left = left + 'px';
    checkinBtn.classList.toggle('active',   mode === 'checkin');
    checkoutBtn.classList.toggle('active',  mode === 'checkout');
    checkinBtn.setAttribute('aria-expanded',  String(mode === 'checkin'));
    checkoutBtn.setAttribute('aria-expanded', String(mode === 'checkout'));
}

function closeCalendar() {
    calendarEl.classList.add('hidden');
    checkinBtn.classList.remove('active');
    checkoutBtn.classList.remove('active');
    checkinBtn.setAttribute('aria-expanded', 'false');
    checkoutBtn.setAttribute('aria-expanded', 'false');
    calMode = null;
}

function renderCalendar() {
    const monthNames = ['January','February','March','April','May','June',
                        'July','August','September','October','November','December'];
    calMonthYear.textContent = `${monthNames[calMonth]} ${calYear}`;

    const firstDay    = new Date(calYear, calMonth, 1).getDay();
    const daysInMonth = new Date(calYear, calMonth + 1, 0).getDate();
    const todayRef    = toLocalMidnight(todayStr);
    const maxCheckin  = toLocalMidnight(maxCheckinDate);
    const viewStart   = new Date(calYear, calMonth, 1);
    const viewEnd     = new Date(calYear, calMonth + 1, 0);

    calPrev.disabled = viewStart <= new Date(todayRef.getFullYear(), todayRef.getMonth(), 1);

    if (calMode === 'checkin') {
        calNext.disabled = viewEnd >= maxCheckin;
    } else {
        if (checkinInput.value) {
            const maxCo = toLocalMidnight(checkinInput.value);
            maxCo.setMonth(maxCo.getMonth() + 1);
            calNext.disabled = viewEnd >= maxCo;
        } else {
            calNext.disabled = false;
        }
    }

    calGrid.innerHTML = '';

    for (let i = 0; i < firstDay; i++) {
        const empty = document.createElement('div');
        empty.className = 'cal-day empty';
        empty.setAttribute('aria-hidden', 'true');
        calGrid.appendChild(empty);
    }

    for (let day = 1; day <= daysInMonth; day++) {
        const dateStr = `${calYear}-${String(calMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        const btn     = document.createElement('button');
        btn.type        = 'button';
        btn.className   = 'cal-day';
        btn.textContent = day;
        btn.setAttribute('aria-label', fmt(dateStr));

        if (dateStr === todayStr)            btn.classList.add('today');
        if (dateStr === checkinInput.value)  btn.classList.add('checkin-selected');
        if (dateStr === checkoutInput.value) btn.classList.add('checkout-selected');

        if (checkinInput.value && checkoutInput.value &&
            dateStr > checkinInput.value && dateStr < checkoutInput.value) {
            btn.classList.add('in-range');
        }

        let disabled = false;
        if (calMode === 'checkin') {
            disabled = dateStr < todayStr || dateStr > maxCheckinDate;
        } else {
            const minCo = checkinInput.value
                ? (() => { const d = toLocalMidnight(checkinInput.value); d.setDate(d.getDate() + 1); return new Intl.DateTimeFormat('en-CA').format(d); })()
                : todayStr;
            const maxCo = checkinInput.value
                ? (() => { const d = toLocalMidnight(checkinInput.value); d.setMonth(d.getMonth() + 1); return new Intl.DateTimeFormat('en-CA').format(d); })()
                : maxCheckinDate;
            disabled = dateStr < minCo || dateStr > maxCo;
        }

        if (disabled) {
            btn.disabled = true;
            btn.setAttribute('aria-disabled', 'true');
        } else {
            btn.addEventListener('click', () => selectDate(dateStr));
        }

        calGrid.appendChild(btn);
    }
}

function selectDate(dateStr) {
    if (calMode === 'checkin') {
        checkinInput.value = dateStr;
        checkinBtn.querySelector('span').textContent = fmt(dateStr);
        checkinBtn.classList.add('has-value');

        if (checkoutInput.value && checkoutInput.value <= dateStr) {
            checkoutInput.value = '';
            checkoutBtn.querySelector('span').textContent = 'Pick a Date';
            checkoutBtn.classList.remove('has-value');
        }

        closeCalendar();
        setTimeout(() => openCalendar('checkout'), 120);
    } else {
        checkoutInput.value = dateStr;
        checkoutBtn.querySelector('span').textContent = fmt(dateStr);
        checkoutBtn.classList.add('has-value');
        closeCalendar();
    }
}

calPrev.addEventListener('click', () => {
    calMonth--;
    if (calMonth < 0) { calMonth = 11; calYear--; }
    renderCalendar();
});

calNext.addEventListener('click', () => {
    calMonth++;
    if (calMonth > 11) { calMonth = 0; calYear++; }
    renderCalendar();
});

checkinBtn.addEventListener('click', () => {
    if (calMode === 'checkin') { closeCalendar(); return; }
    openCalendar('checkin');
});

checkoutBtn.addEventListener('click', () => {
    if (calMode === 'checkout') { closeCalendar(); return; }
    openCalendar('checkout');
});

document.addEventListener('click', (e) => {
    if (calendarEl.classList.contains('hidden')) return;
    if (calendarEl.contains(e.target))  return;
    if (checkinBtn.contains(e.target))  return;
    if (checkoutBtn.contains(e.target)) return;
    closeCalendar();
});

// Dynamic rooms
const toggleAddRoomButtonVisibility = () => {
    const count = dynamicRoomsWrapper.querySelectorAll('.room-entry-box').length + 1;
    addRoomOptionBtn.style.display = count >= 5 ? 'none' : 'flex';
};

function createAdditionalRoom(defaultGuests = 2) {
    if ((dynamicRoomsWrapper.querySelectorAll('.room-entry-box').length + 1) >= 5) return;

    const newRoomId = accumulatedRoomCount + 1;
    accumulatedRoomCount = newRoomId;
    const selectId  = `roomGuests${newRoomId}`;
    const roomBoxNode = document.createElement('div');
    roomBoxNode.classList.add('room-entry-box');
    roomBoxNode.setAttribute('data-room-id', newRoomId);
    roomBoxNode.innerHTML = `
        <div class="room-entry-header">
            <span>Room ${newRoomId}</span>
            <button type="button" class="remove-room-trigger">Remove</button>
        </div>
        <div class="form-group" style="margin-bottom: 0;">
            <label for="${selectId}">Guests</label>
            <div class="guest-select" data-select-id="${selectId}">
                <button type="button" class="guest-select-trigger" aria-haspopup="listbox" aria-expanded="false">
                    <span class="guest-select-display">2 Adults</span>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                        <polyline points="6 9 12 15 18 9"></polyline>
                    </svg>
                </button>
                <div class="guest-select-menu hidden" role="listbox" aria-label="Guest count">
                    <button type="button" class="guest-select-option" role="option" data-value="1">1 Adult</button>
                    <button type="button" class="guest-select-option" role="option" data-value="2">2 Adults</button>
                    <button type="button" class="guest-select-option" role="option" data-value="3">3 Adults</button>
                </div>
                <select id="${selectId}" class="room-guests-select guest-select-native" required>
                    <option value="1">1 Adult</option>
                    <option value="2">2 Adults</option>
                    <option value="3">3 Adults</option>
                </select>
            </div>
        </div>
    `;

    dynamicRoomsWrapper.appendChild(roomBoxNode);
    const selectEl = document.getElementById(selectId);
    if (selectEl) selectEl.value = String(defaultGuests);
    initGuestSelect(roomBoxNode.querySelector('.guest-select'));
    roomBoxNode.querySelector('.remove-room-trigger')?.addEventListener('click', () => {
        roomBoxNode.remove();
        reassignRoomLabels();
        toggleAddRoomButtonVisibility();
    });
    toggleAddRoomButtonVisibility();
}

addRoomOptionBtn.addEventListener('click', () => createAdditionalRoom(2));

const reassignRoomLabels = () => {
    const remainingGuests = Array.from(dynamicRoomsWrapper.querySelectorAll('.room-entry-box')).map((box) => {
        const sel = box.querySelector('.room-guests-select');
        return sel ? parseInt(sel.value, 10) : 2;
    });

    dynamicRoomsWrapper.innerHTML = '';
    accumulatedRoomCount = 1;

    remainingGuests.forEach((g) => createAdditionalRoom(Number.isFinite(g) ? g : 2));
};

// Phone input
document.getElementById('phone').addEventListener('input', function () {
    // Allow digits,
    this.value = this.value.replace(/[^\d\s+\-]/g, '');
});

// Step 1
bookingForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (!checkinInput.value || !checkoutInput.value) {
        alert('Please select both check-in and check-out dates.');
        return;
    }
    if (checkinInput.value >= checkoutInput.value) {
        alert('Check-out date must be after check-in date.');
        return;
    }
    if (checkinInput.value > maxCheckinDate) {
        alert('Check-in date cannot be more than 1 month in the future.');
        return;
    }

    const checkinDate    = toLocalMidnight(checkinInput.value);
    const maxAllowedDate = new Date(checkinDate);
    maxAllowedDate.setMonth(maxAllowedDate.getMonth() + 1);
    if (toLocalMidnight(checkoutInput.value) > maxAllowedDate) {
        alert('Maximum stay duration is 1 month.');
        return;
    }

    const submitBtn  = bookingForm.querySelector('button[type="submit"]');
    const origText   = submitBtn.textContent;
    submitBtn.textContent = 'Checking Availability\u2026';
    submitBtn.disabled    = true;

    try {
        const response = await fetch(`${RESORT_CONFIG.API_BASE}/check-availability`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ checkin: checkinInput.value, checkout: checkoutInput.value }),
        });

        const data = await safeJson(response);

        if (response.ok && data) {
            liveDatabaseRooms = data.inventory;
            requestedRooms    = [];

            const room1Select = document.getElementById('roomGuests1');
            requestedRooms.push({
                id: 1,
                guests: parseInt(room1Select?.value || '2', 10),
            });

            dynamicRoomsWrapper.querySelectorAll('.room-entry-box').forEach((panel, i) => {
                requestedRooms.push({
                    id:     i + 2,
                    guests: parseInt(panel.querySelector('.room-guests-select').value, 10),
                });
            });

            // Prune stale
            const activeRoomIds = new Set(requestedRooms.map(r => r.id));
            for (const storedRoomId in selections) {
                if (!activeRoomIds.has(parseInt(storedRoomId, 10))) delete selections[storedRoomId];
            }

            activeTabId = requestedRooms[0].id;
            transitionToStep(2);
        } else {
            alert(`Availability Check Failed:\n${extractErrorMessage(data)}`);
        }
    } catch (err) {
        console.error('Fetch error:', err);
        alert('Could not connect to the server. Please ensure the backend is running.');
    } finally {
        submitBtn.textContent = origText;
        submitBtn.disabled    = false;
    }
});

// Step 2
function buildRoomTabs() {
    tabsContainer.innerHTML = '<div class="room-tabs-label" aria-hidden="true">Select Room</div>';

    requestedRooms.forEach(room => {
        const btn = document.createElement('button');
        btn.type      = 'button';
        btn.role      = 'tab';
        btn.className = `room-tab ${room.id === activeTabId ? 'active' : ''} ${selections[room.id] ? 'completed' : ''}`;
        btn.setAttribute('aria-selected', String(room.id === activeTabId));
        btn.setAttribute('aria-label',    `Select room type for Room ${room.id}`);
        btn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path></svg>
            <span>Room ${room.id}</span>
        `;
        btn.addEventListener('click', () => {
            activeTabId = room.id;
            updateTabDisplay();
        });
        tabsContainer.appendChild(btn);
    });

    const badge = document.createElement('span');
    badge.id        = 'tabGuestBadge';
    badge.className = 'tab-guest-badge';
    tabsContainer.appendChild(badge);
    updateTabDisplay();
}

function updateTabDisplay() {
    let tabIndex = 0;
    Array.from(tabsContainer.children).forEach((node) => {
        if (!node.classList.contains('room-tab')) return;
        const roomInfo = requestedRooms[tabIndex++];
        if (!roomInfo) return;
        const isActive    = roomInfo.id === activeTabId;
        const isCompleted = !!selections[roomInfo.id];
        node.className = `room-tab ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''}`;
        node.setAttribute('aria-selected', String(isActive));
    });

    const currentRoom = requestedRooms.find(r => r.id === activeTabId);
    if (!currentRoom) return;

    const badge = document.getElementById('tabGuestBadge');
    if (badge) {
        badge.innerHTML = `
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
            ${currentRoom.guests} Guest${currentRoom.guests > 1 ? 's' : ''}
        `;
    }

    renderRoomGrid(currentRoom);
}

function renderRoomGrid(currentRoom) {
    roomGrid.innerHTML = '';

    if (!liveDatabaseRooms?.length) {
        const msg = document.createElement('p');
        msg.style.cssText = 'text-align:center;padding:40px;color:var(--text-muted);font-size:1rem;';
        msg.textContent   = 'Sorry, no rooms are available for these dates.';
        roomGrid.appendChild(msg);
        checkStep2Completion();
        return;
    }

    const roomDetails = {
        single: {
            features: ['Private Balcony', 'AC', 'Smart TV', 'Welcome Drinks', 'Breakfast', 'Free Wi-Fi', 'Daily Housekeeping'],
        },
        twin: {
            features: ['Twin Beds', 'Free Wi-Fi', 'AC', 'Smart TV', 'Welcome Drinks', 'Breakfast', 'Work Desk'],
        },
        triple: {
            features: ['Mini Bar', 'AC', 'Smart TV', 'Welcome Drinks', 'Breakfast', 'Lounge Area', 'Premium Toiletries', 'Room Service'],
        },
    };

    let visibleCount = 0;

    liveDatabaseRooms.forEach(roomType => {
        if (roomType.capacity < currentRoom.guests) return;

        // Count how
        let alreadySelectedCount = 0;
        for (const [tabId, typeId] of Object.entries(selections)) {
            if (parseInt(tabId, 10) !== activeTabId && typeId === roomType.room_type_id) alreadySelectedCount++;
        }
        if (alreadySelectedCount >= roomType.available_count) return;

        visibleCount++;

        const nameLower = roomType.type_name?.toLowerCase() || '';
        let roomImage = 'singleroom.webp';
        let roomKey   = 'single';
        if (nameLower.includes('twin'))   { roomImage = 'doubleroom.webp'; roomKey = 'twin'; }
        if (nameLower.includes('triple')) { roomImage = 'tripleroom.webp'; roomKey = 'triple'; }

        const details    = roomDetails[roomKey];
        const isSelected = selections[activeTabId] === roomType.room_type_id;

        const card = document.createElement('div');
        card.className   = `room-card ${isSelected ? 'selected' : ''}`;
        card.setAttribute('role', 'listitem');
        card.setAttribute('aria-label', roomType.type_name);

        const imageFrame = document.createElement('div');
        imageFrame.className = 'room-image-frame';
        const img = document.createElement('img');
        img.src = roomImage;
        img.alt     = roomType.type_name;
        img.loading = 'lazy';
        imageFrame.appendChild(img);

        const metaDesc = document.createElement('div');
        metaDesc.className = 'room-meta-desc';

        const metaMain = document.createElement('div');
        metaMain.className = 'room-meta-main';

        const h3 = document.createElement('h3');
        h3.textContent = roomType.type_name;

        const capacitySpan = document.createElement('div');
        capacitySpan.className = 'room-capacity-spec';
        capacitySpan.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle></svg> Up to ${roomType.capacity} Guests`;

        const featuresContainer = document.createElement('div');
        featuresContainer.className = 'room-features-container';
        const featLabel = document.createElement('div');
        featLabel.className   = 'room-features-label';
        featLabel.textContent = 'Included Amenities';
        const featList = document.createElement('div');
        featList.className = 'room-features-list';
        details.features.forEach(feat => {
            const tag = document.createElement('span');
            tag.className   = 'room-feature-tag';
            tag.textContent = feat;
            featList.appendChild(tag);
        });
        featuresContainer.appendChild(featLabel);
        featuresContainer.appendChild(featList);

        metaMain.appendChild(h3);
        metaMain.appendChild(capacitySpan);

        const metaAction = document.createElement('div');
        metaAction.className = 'room-meta-action';

        const priceBlock = document.createElement('div');
        priceBlock.className = 'room-price-block';
        const priceLabel = document.createElement('div');
        priceLabel.className   = 'room-price-label';
        priceLabel.textContent = 'Per Night';
        const priceValue = document.createElement('div');
        priceValue.className   = 'room-price-value';
        priceValue.textContent = `Rs. ${Number(roomType.price).toLocaleString('en-IN')}`;
        const priceUnit = document.createElement('div');
        priceUnit.className   = 'room-price-unit';
        priceUnit.textContent = 'incl. breakfast';
        priceBlock.appendChild(priceLabel);
        priceBlock.appendChild(priceValue);
        priceBlock.appendChild(priceUnit);

        const selectBtn = document.createElement('button');
        selectBtn.type        = 'button';
        selectBtn.className   = 'btn-select-choice';
        selectBtn.textContent = isSelected ? '\u2713 Selected' : 'Select Room';
        selectBtn.setAttribute('aria-pressed', String(isSelected));

        metaAction.appendChild(priceBlock);
        metaAction.appendChild(selectBtn);

        const metaBottom = document.createElement('div');
        metaBottom.className = 'room-meta-bottom';
        metaBottom.appendChild(featuresContainer);
        metaBottom.appendChild(metaAction);

        metaDesc.appendChild(metaMain);
        metaDesc.appendChild(metaBottom);
        card.appendChild(imageFrame);
        card.appendChild(metaDesc);

        card.addEventListener('click', () => {
            selections[activeTabId] = roomType.room_type_id;
            // Auto-advance to
            const nextUnselected = requestedRooms.find(r => !selections[r.id]);
            if (nextUnselected) activeTabId = nextUnselected.id;
            updateTabDisplay();
            checkStep2Completion();
        });

        roomGrid.appendChild(card);
    });

    if (visibleCount === 0) {
        const msg = document.createElement('p');
        msg.style.cssText = 'text-align:center;padding:40px;color:var(--text-muted);font-size:1rem;';
        msg.textContent   = 'No available rooms match your criteria, or all matching options have already been selected in your other tabs.';
        roomGrid.appendChild(msg);
    }

    checkStep2Completion();
}

function checkStep2Completion() {
    const allSelected = requestedRooms.every(r => selections[r.id]);
    proceedBtn.disabled = !allSelected;
    proceedBtn.setAttribute('aria-disabled', String(!allSelected));
    proceedBtn.textContent = allSelected ? 'Proceed \u276F' : 'Proceed \u276F';

    const nights   = getNights();
    let totalSum   = 0;
    for (const tabId in selections) {
        const roomInfo = liveDatabaseRooms.find(r => r.room_type_id === selections[tabId]);
        if (roomInfo?.price) {
            totalSum += parseFloat(String(roomInfo.price).replace(/,/g, '')) * nights;
        }
    }

    const totalDisplay = document.getElementById('totalAmountDisplay');
    if (totalDisplay) {
        const nightLabel = nights === 1 ? '1 night' : `${nights} nights`;
        totalDisplay.textContent = '';
        totalDisplay.appendChild(document.createTextNode(`Total (${nightLabel}): `));
        const bold = document.createElement('b');
        bold.textContent = `Rs. ${totalSum.toLocaleString('en-IN')}`;
        totalDisplay.appendChild(bold);
    }
}

function getNights() {
    if (!checkinInput.value || !checkoutInput.value) return 0;
    return Math.max(0, Math.round(
        (toLocalMidnight(checkoutInput.value) - toLocalMidnight(checkinInput.value)) / 86_400_000
    ));
}

proceedBtn.addEventListener('click', () => {
    if (!proceedBtn.disabled) transitionToStep(3);
});

// Step 3
guestDetailsForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const roomTypeIds = Object.values(selections).map(val => parseInt(val, 10));
    if (roomTypeIds.length === 0) {
        alert('Please select at least one room before confirming.');
        return;
    }

    const fullName = document.getElementById('fullName').value.trim();
    const phone    = document.getElementById('phone').value.trim();
    const email    = (document.getElementById('email') || {}).value?.trim() || '';

    // Basic client-side validation
    if (!fullName) { alert('Please enter your full name.'); return; }
    if (!phone || !/^[\d\s\+\-()]{7,20}$/.test(phone)) {
        alert('Please enter a valid phone number.');
        return;
    }

    const payload = {
        checkin:       checkinInput.value,
        checkout:      checkoutInput.value,
        room_type_ids: roomTypeIds,
        guest:         { full_name: fullName, email, phone },
    };

    const submitBtn = guestDetailsForm.querySelector('button[type="submit"]');
    const origText  = submitBtn.textContent;
    submitBtn.textContent = 'Processing\u2026';
    submitBtn.disabled    = true;

    try {
        const response = await fetch(`${RESORT_CONFIG.API_BASE}/reserve`, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify(payload),
        });

        const data = await safeJson(response);

        if (response.ok && data) {
            guestDetailsForm.classList.add('hidden');
            successMessage.classList.remove('hidden');
            wizardBackBtn.classList.add('hidden');
            wizardSubtitle.textContent = 'Reservation Complete';

            const successDetails = document.getElementById('successDetails');
            if (successDetails) {
                successDetails.textContent = 'Thank you for choosing Natura Resort — we look forward to welcoming you!';
            }

            [step1Panel, step2Panel, step3Panel].forEach(scrollPanelToTop);
        } else {
            alert(`Booking Failed:\n${extractErrorMessage(data)}`);
        }
    } catch (error) {
        console.error('Reservation error:', error);
        alert('Could not connect to the server. Please ensure the backend is running.');
    } finally {
        submitBtn.textContent = origText;
        submitBtn.disabled    = false;
    }
});

closeWizardSuccessBtn.addEventListener('click', () => closeWizard());

document.querySelectorAll('.guest-select').forEach(initGuestSelect);