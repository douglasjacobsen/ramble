// Copyright 2022-2026 The Ramble Authors
//
// Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
// https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
// <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
// option. This file may not be copied, modified, or distributed
// except according to those terms.

(function () {
  'use strict';

  const STORAGE_KEY = 'ramble_completed_tutorials';
  const GOALS_STORAGE_KEY = 'ramble_selected_goals';
  const APP_STORAGE_KEY = 'ramble_selected_app';
  const DEFAULT_APP = 'wrf';

  function getStoredSelectedApp() {
    try {
      const stored = localStorage.getItem(APP_STORAGE_KEY);
      return stored || DEFAULT_APP;
    } catch (e) {
      return DEFAULT_APP;
    }
  }

  function storeSelectedApp(appKey) {
    try {
      localStorage.setItem(APP_STORAGE_KEY, appKey);
    } catch (e) {
      console.warn('Could not save selected application:', e);
    }
  }

  function updateAppVariants(selectedApp) {
    // 1. Update all variant containers on page
    const variants = document.querySelectorAll('.tn-app-variant');
    if (variants.length > 0) {
      let activeApp = selectedApp;
      const hasMatch = document.querySelector(`.tn-app-variant.tn-app-${selectedApp}`);
      if (!hasMatch) {
        for (const v of variants) {
          const match = v.className.match(/tn-app-([a-zA-Z0-9_\-]+)/);
          if (match && match[1] !== 'variant') {
            activeApp = match[1];
            break;
          }
        }
      }

      variants.forEach((el) => {
        if (el.classList.contains(`tn-app-${activeApp}`)) {
          el.classList.add('active');
          el.style.display = 'block';
        } else {
          el.classList.remove('active');
          el.style.display = 'none';
        }
      });
    }

    // 2. Update all app buttons and cards across document
    document.querySelectorAll('.tn-app-btn').forEach((btn) => {
      const app = btn.getAttribute('data-app');
      const checkEl = btn.querySelector('.tn-app-btn-check');
      if (app === selectedApp) {
        btn.classList.add('active');
        btn.setAttribute('aria-pressed', 'true');
        if (checkEl) checkEl.textContent = '✓';
      } else {
        btn.classList.remove('active');
        btn.setAttribute('aria-pressed', 'false');
        if (checkEl) checkEl.textContent = '';
      }
    });

    document.querySelectorAll('.tn-app-pref-card').forEach((card) => {
      const app = card.getAttribute('data-app');
      const radio = card.querySelector('input[type="radio"]');
      if (app === selectedApp) {
        card.classList.add('active');
        card.setAttribute('aria-checked', 'true');
        if (radio) radio.checked = true;
      } else {
        card.classList.remove('active');
        card.setAttribute('aria-checked', 'false');
        if (radio) radio.checked = false;
      }
    });
  }

  function setSelectedApp(appKey) {
    storeSelectedApp(appKey);
    updateAppVariants(appKey);
  }

  function getCompletedTutorials() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored ? JSON.parse(stored) : {};
    } catch (e) {
      return {};
    }
  }

  function setTutorialCompleted(tutorialKey, isCompleted) {
    try {
      const completed = getCompletedTutorials();
      if (isCompleted) {
        completed[tutorialKey] = true;
      } else {
        delete completed[tutorialKey];
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(completed));
    } catch (e) {
      console.warn('Could not save tutorial progress:', e);
    }
  }

  function getStoredSelectedGoals() {
    try {
      const stored = localStorage.getItem(GOALS_STORAGE_KEY);
      return stored ? JSON.parse(stored) : null;
    } catch (e) {
      return null;
    }
  }

  function storeSelectedGoals(selectedKeys) {
    try {
      localStorage.setItem(GOALS_STORAGE_KEY, JSON.stringify(selectedKeys));
    } catch (e) {
      console.warn('Could not save selected goals:', e);
    }
  }

  function parseDurationToMinutes(durationStr) {
    if (!durationStr) return 0;
    const match = durationStr.match(/(\d+)/);
    return match ? parseInt(match[1], 10) : 0;
  }

  function formatMinutes(minutes) {
    if (minutes < 60) {
      return `${minutes} min`;
    }
    const hrs = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hrs}h ${mins}m` : `${hrs}h`;
  }

  function initNavigator() {
    const container = document.getElementById('tutorial-navigator-app');
    if (!container) {
      return;
    }

    const data = window.RAMBLE_TUTORIAL_DATA;
    if (!data || !data.tutorials || !data.goals) {
      container.innerHTML = `
        <div class="tn-error">
          <p><strong>Note:</strong> Tutorial pathway data is loading or not available.</p>
        </div>
      `;
      return;
    }

    const tutorials = data.tutorials;
    const goals = data.goals;

    // Restore previously selected goals or default to the first goal
    let storedGoals = getStoredSelectedGoals();
    let selectedGoalKeys = new Set(
      Array.isArray(storedGoals) && storedGoals.length > 0
        ? storedGoals.filter((k) => goals[k])
        : [Object.keys(goals)[0]]
    );

    // Render skeleton layout
    container.innerHTML = `
      <div class="tn-container">
        <div class="tn-header">
          <h3 class="tn-title">🎯 Interactive Learning Pathway Navigator</h3>
          <p class="tn-subtitle">
            Select one or more end goals to generate a customized, step-by-step tutorial curriculum.
          </p>
        </div>

        <div class="tn-goals-section">
          <div class="tn-section-heading">
            <span class="tn-heading-text">1. Choose Your End Goals (Select one or more)</span>
            <div class="tn-goal-actions">
              <button type="button" class="tn-btn tn-btn-sm" id="tn-select-all-goals">Select All</button>
              <button type="button" class="tn-btn tn-btn-sm" id="tn-clear-goals">Clear All</button>
            </div>
          </div>
          <div class="tn-goals-list" id="tn-goals-list"></div>
        </div>

        <div class="tn-summary-bar" id="tn-summary-bar"></div>

        <div class="tn-apps-section">
          <div class="tn-section-heading">
            <span class="tn-heading-text">2. Choose Preferred Application (for multi-application tutorials)</span>
          </div>
          <p class="tn-apps-desc">
            Some tutorials (such as Scaling Studies) support multiple application workloads. Select your preferred application to follow throughout those tutorials:
          </p>
          <div class="tn-apps-grid" id="tn-apps-grid"></div>
        </div>

        <div class="tn-pathway-section">
          <div class="tn-section-heading">
            <span class="tn-heading-text">3. Recommended Learning Path</span>
          </div>
          <div class="tn-pathway-list" id="tn-pathway-list"></div>
        </div>
      </div>
    `;

    const goalsList = container.querySelector('#tn-goals-list');
    const summaryBar = container.querySelector('#tn-summary-bar');
    const pathwayList = container.querySelector('#tn-pathway-list');
    const selectAllBtn = container.querySelector('#tn-select-all-goals');
    const clearBtn = container.querySelector('#tn-clear-goals');

    function renderGoals() {
      goalsList.innerHTML = Object.entries(goals)
        .map(([key, goal]) => {
          const isSelected = selectedGoalKeys.has(key);
          const icon = goal.icon || '📌';
          return `
            <div class="tn-goal-item ${isSelected ? 'selected' : ''}" data-goal-key="${key}" tabindex="0" role="checkbox" aria-checked="${isSelected}">
              <div class="tn-goal-checkbox">
                <input type="checkbox" ${isSelected ? 'checked' : ''} tabindex="-1" aria-hidden="true" />
              </div>
              <div class="tn-goal-content">
                <div class="tn-goal-header">
                  <span class="tn-goal-icon">${icon}</span>
                  <span class="tn-goal-title">${goal.title}</span>
                  <span class="tn-badge tn-badge-steps">${(goal.tutorials || []).length} steps</span>
                </div>
                <div class="tn-goal-desc">${goal.description || ''}</div>
              </div>
            </div>
          `;
        })
        .join('');
    }

    function calculatePathway() {
      if (selectedGoalKeys.size === 0) {
        return [];
      }

      // Map: tutorialKey -> Set of goalKeys that require it
      const tutorialGoalMap = new Map();

      selectedGoalKeys.forEach((goalKey) => {
        const goal = goals[goalKey];
        if (!goal || !Array.isArray(goal.tutorials)) return;

        goal.tutorials.forEach((tutKey) => {
          if (!tutorials[tutKey]) return;
          if (!tutorialGoalMap.has(tutKey)) {
            tutorialGoalMap.set(tutKey, new Set());
          }
          tutorialGoalMap.get(tutKey).add(goalKey);
        });
      });

      // Deduplicated tutorials sorted by progressive order_rank
      const orderedTutorials = Array.from(tutorialGoalMap.keys())
        .map((tutKey) => ({
          key: tutKey,
          ...tutorials[tutKey],
          requiredByGoals: Array.from(tutorialGoalMap.get(tutKey)),
        }))
        .sort((a, b) => {
          const rankA = a.order_rank !== undefined ? a.order_rank : 999;
          const rankB = b.order_rank !== undefined ? b.order_rank : 999;
          return rankA - rankB;
        });

      return orderedTutorials;
    }

    function renderPathway() {
      const pathway = calculatePathway();
      const completedMap = getCompletedTutorials();

      // Render summary bar
      if (selectedGoalKeys.size === 0) {
        summaryBar.innerHTML = `
          <div class="tn-empty-notice">
            <span>👈 Please select at least one end goal above to see your tutorial roadmap.</span>
          </div>
        `;
        pathwayList.innerHTML = `
          <div class="tn-pathway-empty">
            <p>No goals selected. Choose what you want to achieve above to see recommended tutorials.</p>
          </div>
        `;
        return;
      }

      const totalTutorials = pathway.length;
      let totalMinutes = 0;
      let completedCount = 0;

      pathway.forEach((tut) => {
        totalMinutes += parseDurationToMinutes(tut.duration);
        if (completedMap[tut.key]) {
          completedCount++;
        }
      });

      const percent = totalTutorials > 0 ? Math.round((completedCount / totalTutorials) * 100) : 0;

      summaryBar.innerHTML = `
        <div class="tn-summary-content">
          <div class="tn-summary-metrics">
            <span class="tn-metric"><strong>${selectedGoalKeys.size}</strong> goal${selectedGoalKeys.size > 1 ? 's' : ''} selected</span>
            <span class="tn-metric-dot">•</span>
            <span class="tn-metric"><strong>${totalTutorials}</strong> tutorial${totalTutorials > 1 ? 's' : ''} total</span>
            <span class="tn-metric-dot">•</span>
            <span class="tn-metric">Estimated time: <strong>${formatMinutes(totalMinutes)}</strong></span>
            <span class="tn-metric-dot">•</span>
            <span class="tn-metric">Progress: <strong>${completedCount}/${totalTutorials}</strong> (${percent}%)</span>
          </div>
          <div class="tn-progress-bar-bg">
            <div class="tn-progress-bar-fill" style="width: ${percent}%;"></div>
          </div>
        </div>
      `;

      // Render step-by-step pathway list
      pathwayList.innerHTML = pathway
        .map((tut, index) => {
          const isCompleted = !!completedMap[tut.key];
          const levelClass = (tut.level || 'beginner').toLowerCase();
          const goalBadges = tut.requiredByGoals
            .map((gKey) => {
              const g = goals[gKey];
              return `<span class="tn-goal-tag">${g ? (g.icon ? g.icon + ' ' : '') + g.title : gKey}</span>`;
            })
            .join(' ');

          return `
            <div class="tn-step-card ${isCompleted ? 'is-completed' : ''}" data-tutorial-key="${tut.key}">
              <div class="tn-step-num-col">
                <span class="tn-step-num">Step ${index + 1}</span>
                <label class="tn-complete-toggle" title="Mark as finished">
                  <input type="checkbox" class="tn-complete-checkbox" ${isCompleted ? 'checked' : ''} />
                  <span class="tn-complete-label">Done</span>
                </label>
              </div>
              <div class="tn-step-main">
                <div class="tn-step-header">
                  <a href="${tut.url}" class="tn-step-title-link">
                    ${tut.title}
                  </a>
                  <div class="tn-step-badges">
                    <span class="tn-badge tn-badge-${levelClass}">${tut.level || 'Tutorial'}</span>
                    ${tut.duration ? `<span class="tn-badge tn-badge-time">⏱️ ${tut.duration}</span>` : ''}
                  </div>
                </div>
                <div class="tn-step-desc">${tut.description || ''}</div>
                <div class="tn-step-footer">
                  <div class="tn-step-goals">
                    <span class="tn-goals-label">Required for:</span>
                    ${goalBadges}
                  </div>
                  <a href="${tut.url}" class="tn-btn tn-btn-open">
                    Open Tutorial →
                  </a>
                </div>
              </div>
            </div>
          `;
        })
        .join('');

      // Attach complete toggle handlers
      pathwayList.querySelectorAll('.tn-complete-checkbox').forEach((box) => {
        box.addEventListener('change', (e) => {
          const stepCard = e.target.closest('.tn-step-card');
          const tutKey = stepCard.getAttribute('data-tutorial-key');
          setTutorialCompleted(tutKey, e.target.checked);
          renderPathway();
        });
      });
    }

    // Goal click handlers
    goalsList.addEventListener('click', (e) => {
      const item = e.target.closest('.tn-goal-item');
      if (!item) return;
      const key = item.getAttribute('data-goal-key');
      if (selectedGoalKeys.has(key)) {
        selectedGoalKeys.delete(key);
      } else {
        selectedGoalKeys.add(key);
      }
      storeSelectedGoals(Array.from(selectedGoalKeys));
      renderGoals();
      renderPathway();
    });

    goalsList.addEventListener('keydown', (e) => {
      if (e.key === ' ' || e.key === 'Enter') {
        const item = e.target.closest('.tn-goal-item');
        if (item) {
          e.preventDefault();
          item.click();
        }
      }
    });

    selectAllBtn.addEventListener('click', () => {
      selectedGoalKeys = new Set(Object.keys(goals));
      storeSelectedGoals(Array.from(selectedGoalKeys));
      renderGoals();
      renderPathway();
    });

    clearBtn.addEventListener('click', () => {
      selectedGoalKeys.clear();
      storeSelectedGoals([]);
      renderGoals();
      renderPathway();
    });

    function renderApps() {
      const apps = data.selectable_applications || {
        wrf: {
          name: 'WRF',
          workload: 'CONUS_12km',
          description: 'Weather Research and Forecasting atmospheric model'
        },
        gromacs: {
          name: 'GROMACS',
          workload: 'water_bare',
          description: 'Molecular dynamics simulation package'
        }
      };

      const selectedApp = getStoredSelectedApp();
      const appsGrid = container.querySelector('#tn-apps-grid');
      if (!appsGrid) return;

      appsGrid.innerHTML = Object.entries(apps)
        .map(([key, app]) => {
          const isSelected = key === selectedApp;
          return `
            <div class="tn-app-pref-card ${isSelected ? 'active' : ''}" data-app="${key}" tabindex="0" role="radio" aria-checked="${isSelected}">
              <div class="tn-app-pref-radio">
                <input type="radio" name="tn-pref-app" value="${key}" ${isSelected ? 'checked' : ''} tabindex="-1" />
              </div>
              <div class="tn-app-pref-info">
                <div class="tn-app-pref-title-row">
                  <span class="tn-app-pref-name">${app.name || key}</span>
                  <span class="tn-badge tn-badge-time">Workload: ${app.workload || 'default'}</span>
                </div>
                <div class="tn-app-pref-desc">${app.description || ''}</div>
              </div>
            </div>
          `;
        })
        .join('');

      appsGrid.querySelectorAll('.tn-app-pref-card').forEach((card) => {
        card.addEventListener('click', () => {
          const key = card.getAttribute('data-app');
          setSelectedApp(key);
        });
        card.addEventListener('keydown', (e) => {
          if (e.key === ' ' || e.key === 'Enter') {
            e.preventDefault();
            card.click();
          }
        });
      });
    }

    // Hide tutorial sub-pages listing from the left sidebar if present
    const activeSidebarTutorialUl = document.querySelector('.wy-menu-vertical li.toctree-l1.current > a[href="#"] + ul');
    if (activeSidebarTutorialUl) {
      activeSidebarTutorialUl.style.display = 'none';
    }

    // Initial render
    renderGoals();
    renderApps();
    renderPathway();
  }

  function initAppSwitchers() {
    const data = window.RAMBLE_TUTORIAL_DATA || {};
    const selectableApps = data.selectable_applications || {
      wrf: {
        name: 'WRF',
        workload: 'CONUS_12km',
        description: 'Weather Research and Forecasting atmospheric model'
      },
      gromacs: {
        name: 'GROMACS',
        workload: 'water_bare',
        description: 'Molecular dynamics simulation package'
      }
    };

    let switchers = Array.from(document.querySelectorAll('.tn-app-switcher'));

    // If there are variants on page but no switcher, auto-insert one before the first variant
    const variants = document.querySelectorAll('.tn-app-variant');
    if (switchers.length === 0 && variants.length > 0) {
      const firstVariant = variants[0];
      const autoSwitcher = document.createElement('div');
      autoSwitcher.className = 'tn-app-switcher';
      firstVariant.parentNode.insertBefore(autoSwitcher, firstVariant);
      switchers.push(autoSwitcher);
    }

    const currentApp = getStoredSelectedApp();

    switchers.forEach((switcher) => {
      let apps = selectableApps;
      const recipeId = switcher.getAttribute('data-recipe');
      if (recipeId && data.recipes && data.recipes[recipeId] && data.recipes[recipeId].apps) {
        apps = data.recipes[recipeId].apps;
      }

      switcher.innerHTML = `
        <div class="tn-app-switcher-card">
          <div class="tn-app-switcher-header">
            <span class="tn-app-switcher-title">⚙️ Select Application:</span>
            <span class="tn-app-switcher-subtitle">Choose an application to customize all code examples and configurations in this tutorial:</span>
          </div>
          <div class="tn-app-btn-group" role="group" aria-label="Tutorial application switcher">
            ${Object.entries(apps)
              .map(([appKey, appInfo]) => {
                const isActive = appKey === currentApp;
                return `
                  <button type="button" class="tn-app-btn ${isActive ? 'active' : ''}" data-app="${appKey}" aria-pressed="${isActive}">
                    <span class="tn-app-btn-check">${isActive ? '✓' : ''}</span>
                    <span class="tn-app-btn-name">${appInfo.name || appKey}</span>
                    ${appInfo.workload ? `<span class="tn-app-btn-workload">${appInfo.workload}</span>` : ''}
                  </button>
                `;
              })
              .join('')}
          </div>
          <div class="tn-app-switcher-hint">
            💡 Selection is preserved across tutorials and automatically configures relevant commands and YAML configs.
          </div>
        </div>
      `;

      switcher.querySelectorAll('.tn-app-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
          const app = btn.getAttribute('data-app');
          setSelectedApp(app);
        });
      });
    });

    updateAppVariants(currentApp);
  }

  window.addEventListener('storage', (e) => {
    if (e.key === APP_STORAGE_KEY) {
      updateAppVariants(e.newValue || DEFAULT_APP);
    }
  });

  function initializeAll() {
    initNavigator();
    initAppSwitchers();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeAll);
  } else {
    initializeAll();
  }
})();
