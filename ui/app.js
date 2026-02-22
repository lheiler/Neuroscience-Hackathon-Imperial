// Global State
let profiles = [];

// DOM Elements
const profilesGrid = document.getElementById('profiles-grid');
const modalOverlay = document.getElementById('modal-overlay');
const btnCreateNew = document.getElementById('btn-create-new');
const btnCloseModal = document.getElementById('btn-close-modal');
const btnCancelModal = document.getElementById('btn-cancel-modal');
const profileForm = document.getElementById('profile-form');

// Dashboard Elements
const activeDashboard = document.getElementById('active-dashboard');
const activeBadge = document.getElementById('active-badge');
const activeAvatar = document.getElementById('active-avatar');
const activeName = document.getElementById('active-name');
const activeHeadset = document.getElementById('active-headset');
const statTime = document.getElementById('stat-time');
const statAcc = document.getElementById('stat-acc');
const profileStatsGrid = document.getElementById('profile-stats-grid');
const calibrationWarning = document.getElementById('calibration-warning');

const btnCalibrate = document.getElementById('btn-calibrate');
const btnStartSession = document.getElementById('btn-start-session');
const btnDashStartSession = document.getElementById('btn-dash-start-session');
const btnGoDashboard = document.getElementById('btn-go-dashboard');
const btnBackToProfiles = document.getElementById('btn-back-to-profiles');
const btnDeleteProfile = document.getElementById('btn-delete-profile');


// Helper to get initials for avatar
function getInitials(name) {
    const parts = name.split(' ');
    if (parts.length > 1) {
        return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
}

// Render Profiles to the Grid
function renderProfiles() {
    profilesGrid.innerHTML = '';

    if (profiles.length === 0) {
        profilesGrid.innerHTML = `
            <div style="color: var(--text-muted); padding: 24px; text-align: center; grid-column: 1 / -1;">
                No profiles found. Create one to get started.
            </div>
        `;
        activeDashboard.classList.add('hidden');
        return;
    }

    let activeFound = null;

    profiles.forEach(profile => {
        const card = document.createElement('div');
        card.className = `profile-card ${profile.isActive ? 'active-profile' : ''}`;
        card.dataset.id = profile.id;

        const initials = getInitials(profile.name);

        card.innerHTML = `
            <div class="card-header">
                <div class="avatar">${initials}</div>
                ${profile.isActive ? '<i class="fa-solid fa-check-circle" style="color: var(--primary); z-index:2;"></i>' : ''}
            </div>
            <div class="card-body">
                <h3 class="profile-name">${profile.name}</h3>
                <div class="profile-meta">
                    <i class="fa-solid fa-clock-rotate-left"></i> ${profile.lastActive || 'Recently'}
                </div>
            </div>
            <div class="card-footer">
                <span class="badge">${profile.weights_status || 'Initialized'}</span>
                <i class="fa-solid fa-headset" style="color: var(--text-muted);" title="${profile.headsetDisplay}"></i>
            </div>
        `;

        // Add Click listener to make active
        card.addEventListener('click', () => {
            setActiveProfile(profile.id);
        });

        profilesGrid.appendChild(card);

        if (profile.isActive) activeFound = profile;
    });

    if (activeFound) {
        updateDashboard(activeFound);
    } else {
        activeDashboard.classList.add('hidden');
    }
}

// Update the right-side dashboard panel
function updateDashboard(profile) {
    activeDashboard.classList.remove('hidden');

    activeAvatar.innerText = getInitials(profile.name);
    activeName.innerText = profile.name;
    activeHeadset.innerHTML = `<i class="fa-solid fa-headset"></i> ${profile.headsetDisplay}`;

    // Check calibration state
    const isCalibrated = profile.calibration_status === 'calibrated';

    if (isCalibrated) {
        activeBadge.innerText = 'Ready';
        activeBadge.className = 'badge badge-success';

        calibrationWarning.classList.add('hidden');
        profileStatsGrid.classList.remove('opacity-30');

        btnCalibrate.classList.add('hidden');
        btnStartSession.classList.remove('hidden');
        btnGoDashboard.classList.remove('hidden');

        if (btnDashStartSession) {
            btnDashStartSession.classList.remove('opacity-30');
            btnDashStartSession.disabled = false;
        }
    } else {
        activeBadge.innerText = 'Uncalibrated';
        activeBadge.className = 'badge badge-warning';

        calibrationWarning.classList.remove('hidden');
        profileStatsGrid.classList.add('opacity-30');

        btnCalibrate.classList.remove('hidden');
        btnStartSession.classList.add('hidden');
        btnGoDashboard.classList.add('hidden');

        if (btnDashStartSession) {
            btnDashStartSession.classList.add('opacity-30');
            btnDashStartSession.disabled = true;
        }
    }

    // Fallbacks just in case backend didn't init them
    const usage = profile.usage_data || { total_time_min: 0, sessions: 0, avg_accuracy: 0.0, last_prediction: '--' };

    if (statTime) statTime.innerText = `${usage.total_time_min}m`;
    if (statAcc) statAcc.innerText = `${usage.avg_accuracy.toFixed(1)}%`;
    statSessions.innerText = usage.sessions;
    statLast.innerText = usage.last_prediction;
}

// Fetch Profiles from Backend API
async function fetchProfiles(retries = 3) {
    try {
        const response = await fetch('/api/profiles');
        if (response.ok) {
            profiles = await response.json();

            // If we have profiles, ensure one is active visually (for demo purposes)
            if (profiles.length > 0 && !profiles.some(p => p.isActive)) {
                profiles[0].isActive = true;
            }

            renderProfiles();
        } else {
            console.error('Failed to fetch profiles:', response.statusText);
            profilesGrid.innerHTML = '<div style="color: var(--danger); padding: 24px;">Error loading profiles from server.</div>';
        }
    } catch (error) {
        if (retries > 0) {
            console.log(`Retrying fetch... (${retries} left)`);
            setTimeout(() => fetchProfiles(retries - 1), 1000);
        } else {
            console.error('Error fetching profiles:', error);
            profilesGrid.innerHTML = '<div style="color: var(--danger); padding: 24px;">Cannot connect to backend server. Make sure server.py is running.</div>';
        }
    }
}

// Set a profile as active (Locally for now, could be an API call if needed)
function setActiveProfile(id) {
    profiles.forEach(p => {
        p.isActive = (p.id === id);
    });
    renderProfiles();

    // Simulate connection update logically
    console.log(`Switched active context to profile ID: ${id}`);
}

// Modal Handling
function openModal() {
    modalOverlay.classList.remove('hidden');
    document.getElementById('subject-name').focus();
}

function closeModal() {
    modalOverlay.classList.add('hidden');
    profileForm.reset();
}

btnCreateNew.addEventListener('click', openModal);
btnCloseModal.addEventListener('click', closeModal);
btnCancelModal.addEventListener('click', (e) => {
    e.preventDefault();
    closeModal();
});

// Close modal if clicking outside
modalOverlay.addEventListener('click', (e) => {
    if (e.target === modalOverlay) closeModal();
});

// Navigation & View Toggling
const linkProfiles = document.getElementById('link-profiles');
const linkDashboard = document.getElementById('link-dashboard');
const viewProfiles = document.getElementById('view-profiles');
const viewDashboard = document.getElementById('view-dashboard');

function switchView(viewName) {
    // Reset active states
    linkProfiles.parentElement.classList.remove('active');
    linkDashboard.parentElement.classList.remove('active');

    viewProfiles.classList.add('hidden');
    viewDashboard.classList.add('hidden');

    if (viewName === 'profiles') {
        linkProfiles.parentElement.classList.add('active');
        viewProfiles.classList.remove('hidden');
    } else if (viewName === 'dashboard') {
        linkDashboard.parentElement.classList.add('active');
        viewDashboard.classList.remove('hidden');
        renderFullDashboard();
    }
}

linkProfiles.addEventListener('click', (e) => { e.preventDefault(); switchView('profiles'); });
linkDashboard.addEventListener('click', (e) => { e.preventDefault(); switchView('dashboard'); });
if (document.getElementById('btn-go-dashboard')) {
    document.getElementById('btn-go-dashboard').addEventListener('click', () => switchView('dashboard'));
}
if (document.getElementById('btn-back-to-profiles')) {
    document.getElementById('btn-back-to-profiles').addEventListener('click', () => switchView('profiles'));
}


// Handle Form Submission and sending to Backend
profileForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const nameInput = document.getElementById('subject-name').value;
    const headsetSelect = document.getElementById('headset-config');

    if (!nameInput || !headsetSelect.value) return;

    // Create new profile object matching backend schema (weights are handled by backend)
    const newProfile = {
        id: Date.now().toString(),
        name: nameInput,
        headset: headsetSelect.value,
        headsetDisplay: headsetSelect.options[headsetSelect.selectedIndex].text,
        lastActive: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        isActive: true, // Make it active immediately
        calibration_status: 'uncalibrated',
        usage_data: {
            total_time_min: 0,
            sessions: 0,
            avg_accuracy: 0.0,
            last_prediction: "--"
        }
    };

    try {
        const response = await fetch('/api/profiles', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(newProfile)
        });

        if (response.ok) {
            const result = await response.json();

            // Deactivate others
            profiles.forEach(p => p.isActive = false);

            const savedProfile = result.profile;
            savedProfile.isActive = true;

            // Add and re-render
            profiles.unshift(savedProfile);
            renderProfiles();
            closeModal();

            // Stay on profiles view to show uncalibrated status and prompt calibration

        } else {
            console.error('Failed to save profile on server');
            alert('Failed to save profile. Please ensure the backend is running.');
        }

    } catch (error) {
        console.error('Error saving profile:', error);
        alert('Could not connect to server.');
    }
});


// ==========================================
// Delete Profile Logic
// ==========================================
if (btnDeleteProfile) {
    btnDeleteProfile.addEventListener('click', async () => {
        const activeProf = profiles.find(p => p.isActive);
        if (!activeProf) return;

        const confirmDelete = confirm(`Are you sure you want to delete profile "${activeProf.name}" and its associated model weights? This action cannot be undone.`);
        if (!confirmDelete) return;

        try {
            const response = await fetch(`/api/profiles/${activeProf.id}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                // Remove locally
                profiles = profiles.filter(p => p.id !== activeProf.id);
                renderProfiles(); // Will hide the dashboard if empty
            } else {
                alert("Failed to delete profile from server.");
            }
        } catch (e) {
            console.error(e);
            alert("Error connecting to server to delete profile.");
        }
    });
}


// ==========================================
// User Flow: Calibration & Live Session
// ==========================================
const calibOverlay = document.getElementById('calibration-overlay');
const calibProgress = document.getElementById('calib-progress');
const calibTitle = document.getElementById('calib-title');
const calibDesc = document.getElementById('calib-desc');

btnCalibrate.addEventListener('click', () => {
    const activeProf = profiles.find(p => p.isActive);
    if (!activeProf) return;

    // Show Loader
    calibOverlay.classList.remove('hidden');
    calibTitle.innerText = "Calibrating Headset...";
    calibDesc.innerText = "Please remain still and follow the on-screen prompts.";
    calibProgress.style.width = '0%';

    // Simulate Calibration Progress
    let val = 0;
    const interval = setInterval(() => {
        val += Math.random() * 8;
        if (val >= 100) {
            val = 100;
            clearInterval(interval);

            calibProgress.style.width = '100%';
            calibTitle.innerText = "Calibration Complete!";
            calibTitle.style.color = "var(--success)";
            calibDesc.innerText = "Syncing generated weights...";

            // Update Backend
            setTimeout(async () => {
                activeProf.calibration_status = 'calibrated';

                try {
                    await fetch('/api/profiles', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(activeProf)
                    });

                    calibOverlay.classList.add('hidden');
                    calibTitle.style.color = "";
                    renderProfiles();
                } catch (e) {
                    alert("Error saving calibration state to backend!");
                }
            }, 800);
        } else {
            calibProgress.style.width = val + '%';
        }
    }, 150);
});

// Start Session Logic Builder
function initiateSessionFlow() {
    const activeProf = profiles.find(p => p.isActive);
    if (!activeProf) return;
    if (activeProf.calibration_status !== 'calibrated') return; // Strict block

    // Simulate session start visually, then navigate to Dashboard
    calibOverlay.classList.remove('hidden');
    calibTitle.innerText = "Starting Live Decoder...";
    calibTitle.style.color = "var(--primary)";
    calibDesc.innerText = "Connecting to streaming server...";
    calibProgress.style.width = '0%';

    setTimeout(() => {
        calibProgress.style.width = '100%';
        setTimeout(() => {
            calibOverlay.classList.add('hidden');
            switchView('dashboard');
        }, 500);
    }, 800);
}

btnStartSession.addEventListener('click', initiateSessionFlow);
if (btnDashStartSession) {
    btnDashStartSession.addEventListener('click', initiateSessionFlow);
}


// ==========================================
// Chart JS Dashboard Logic
// ==========================================
let accuracyChartInstance = null;
let distChartInstance = null;

// Sets up standard design choices for Charts
Chart.defaults.color = '#94a3b8';
Chart.defaults.font.family = "'Inter', sans-serif";

function generateMockTimelineData(baseAccuracy, numSessions) {
    if (numSessions === 0) return { labels: [], data: [] };

    const data = [];
    const labels = [];

    // Simulate a learning curve converging roughly around avgAccuracy
    let currentAcc = Math.max(30, baseAccuracy - 20); // start lower

    for (let i = 1; i <= Math.min(numSessions, 15); i++) {
        labels.push(`Sess ${i}`);

        // Random walk trending toward base
        const step = (Math.random() - 0.5) * 10;
        const drift = (baseAccuracy - currentAcc) * 0.3; // pull to mean
        currentAcc = Math.min(100, Math.max(20, currentAcc + step + drift));

        data.push(currentAcc.toFixed(1));
    }

    // Ensure final looks close to base
    if (data.length > 0) {
        data[data.length - 1] = baseAccuracy.toFixed(1);
    }

    return { labels, data };
}

function renderFullDashboard() {
    const activeProfile = profiles.find(p => p.isActive);
    const emptyState = document.getElementById('dash-empty-state');
    const header = document.querySelector('#view-dashboard > .header');
    const grid1 = document.querySelector('.huge-stats-grid');
    const grid2 = document.querySelector('.charts-grid');

    if (!activeProfile) {
        emptyState.classList.remove('hidden');
        header.style.opacity = '0.2';
        grid1.style.opacity = '0.2';
        grid2.style.opacity = '0.2';
        return;
    }

    emptyState.classList.add('hidden');
    header.style.opacity = '1';
    grid1.style.opacity = '1';
    grid2.style.opacity = '1';

    // 1. Populate Text Nodes
    document.getElementById('dash-subtitle').innerText = `Viewing data for: ${activeProfile.name} • ${activeProfile.headsetDisplay}`;

    const usage = activeProfile.usage_data || { total_time_min: 0, sessions: 0, avg_accuracy: 0.0 };
    document.getElementById('dash-time').innerHTML = `${usage.total_time_min}<span class="unit">m</span>`;
    document.getElementById('dash-acc').innerHTML = `${usage.avg_accuracy.toFixed(1)}<span class="unit">%</span>`;
    document.getElementById('dash-sessions').innerText = usage.sessions;

    // 2. Render Charts
    renderCharts(usage);
}

function renderCharts(usage) {
    // Destroy previous instances if they exist
    if (accuracyChartInstance) accuracyChartInstance.destroy();
    if (distChartInstance) distChartInstance.destroy();

    const ctxAcc = document.getElementById('accuracyChart').getContext('2d');
    const ctxDist = document.getElementById('distributionChart').getContext('2d');

    // Create Line Chart for Accuracy
    const { labels, data } = generateMockTimelineData(usage.avg_accuracy, usage.sessions);

    // Empty state handling for lack of sessions
    if (labels.length === 0) {
        labels.push('No Sessions', 'Planned');
        data.push(0, 0);
    }

    const gradient = ctxAcc.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(16, 185, 129, 0.4)'); // Success green glow
    gradient.addColorStop(1, 'rgba(16, 185, 129, 0.0)');

    accuracyChartInstance = new Chart(ctxAcc, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Decoding Accuracy (%)',
                data: data,
                borderColor: '#10b981',
                backgroundColor: gradient,
                borderWidth: 3,
                pointBackgroundColor: '#0a0a0f',
                pointBorderColor: '#10b981',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6,
                fill: true,
                tension: 0.4 // Smooth curves
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(0,0,0,0.8)',
                    titleColor: '#fff',
                    bodyColor: '#10b981',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    grid: { color: 'rgba(255, 255, 255, 0.05)' }
                },
                x: {
                    grid: { display: false }
                }
            }
        }
    });

    // Create Doughnut Chart for Command Dist
    // Mocking some spread based off sessions
    let cmdData = [0, 0, 0, 0];
    if (usage.sessions > 0) {
        cmdData = [
            usage.sessions * 4 + Math.floor(Math.random() * 10), // Arriba
            usage.sessions * 3 + Math.floor(Math.random() * 10), // Abajo
            usage.sessions * 2 + Math.floor(Math.random() * 10), // Izquierda
            usage.sessions * 4 + Math.floor(Math.random() * 10)  // Derecha
        ];
    } else {
        cmdData = [1, 1, 1, 1]; // equal empty state
    }

    distChartInstance = new Chart(ctxDist, {
        type: 'doughnut',
        data: {
            labels: ['Arriba', 'Abajo', 'Izquierda', 'Derecha'],
            datasets: [{
                data: cmdData,
                backgroundColor: [
                    '#38bdf8', // Light Blue (Primary)
                    '#818cf8', // Soft Indigo (Accent)
                    '#a78bfa', // Purple
                    '#14b8a6'  // Teal
                ],
                borderWidth: 0,
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true
                    }
                }
            }
        }
    });
}


// Initial Fetch
fetchProfiles();

// Simple connection pulse animation simulation
const pulseDot = document.querySelector('.pulse-dot');
setInterval(() => {
    if (profiles.some(p => p.isActive)) {
        // simulate waiting for headset
        pulseDot.style.background = 'var(--accent)';
        pulseDot.style.boxShadow = '0 0 8px var(--accent)';
        document.querySelector('.status-indicator span').innerText = 'Ready/Waiting for Data...';
    }
}, 5000);
