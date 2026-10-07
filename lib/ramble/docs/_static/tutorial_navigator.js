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

        <div class="tn-pathway-section">
          <div class="tn-section-heading">
            <span class="tn-heading-text">2. Recommended Learning Path</span>
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

    // Hide tutorial sub-pages listing from the left sidebar if present
    const activeSidebarTutorialUl = document.querySelector('.wy-menu-vertical li.toctree-l1.current > a[href="#"] + ul');
    if (activeSidebarTutorialUl) {
      activeSidebarTutorialUl.style.display = 'none';
    }

    // Initial render
    renderGoals();
    renderPathway();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initNavigator);
  } else {
    initNavigator();
  }
})();
