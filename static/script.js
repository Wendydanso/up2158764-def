// Doughnut Center Text Plugin
const doughnutCenterTextPlugin = {
  id: 'doughnutCenterText',
  beforeDraw(chart, args, options) {
      const { width, height, ctx } = chart;
      ctx.save();
  
      const label = options.label || '';
      const value = options.text || '';
  
      ctx.font = `${height / 15}px 'Gill Sans', 'Gill Sans MT', Calibri, 'Trebuchet MS', sans-serif`;
      ctx.fillStyle = "#999";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(label, width / 2, height / 2 - 15);
  
      ctx.font = `${height / 10}px 'Gill Sans', 'Gill Sans MT', Calibri, 'Trebuchet MS', sans-serif`;
      ctx.fillStyle = "#0d0745";
      ctx.fillText(value, width / 2, height / 2 + 15);
  
      ctx.restore();
  }
};

// Main initialization function
function initializeBudgetApp() {
 
  initializeCharts();
  
  
  setupFormValidation();
  

  setDefaultDate();
  
 
  loadAPIData();
  
  
  setupBudgetGoalsForm();
}

// Chart initialization
function initializeCharts() {
  // Budget Pie Chart
  const pieCanvas = document.getElementById("budgetPieChart");
  if (pieCanvas) {
      const ctx = pieCanvas.getContext("2d");
      const totalBudget = 5000;
      const spentAmounts = [500, 1000, 300, 150, 100, 150];
      const remainingAmount = totalBudget - spentAmounts.reduce((a, b) => a + b, 0);

      new Chart(ctx, {
          type: "doughnut",
          data: {
              labels: ["Groceries", "Rent", "Utilities", "Travel", "Investment", "Entertainment"],
              datasets: [{
                  data: spentAmounts,
                  backgroundColor: ["#9b8afc", "#6c5ce7", "#d1d1d1", "#b6b6b6", "#9b9b9b", "#d7d4f5"],
                  borderRadius: 10,
                  borderWidth: 1
              }]
          },
          options: {
              responsive: true,
              cutout: '85%',
              plugins: {
                  legend: { position: 'bottom' },
                  tooltip: {
                      callbacks: {
                          label: function(context) {
                              return `${context.label}: £${context.parsed}`;
                          }
                      }
                  },
                  doughnutCenterText: {
                      label: "Total for month",
                      text: `£${remainingAmount}.00`
                  }
              }
          },
          plugins: [doughnutCenterTextPlugin]
      });
  }

  // Monthly Bar Chart
  const spendingCanvas = document.getElementById('spendingChart');
  if (spendingCanvas) {
      const ctx = spendingCanvas.getContext('2d');
      new Chart(ctx, {
          type: 'bar',
          data: {
              labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
              datasets: [
                  {
                      label: 'Income',
                      backgroundColor: '#9b8afc',
                      borderRadius: 20,
                      data: [1000, 1200, 900, 1500, 1300],
                  },
                  {
                      label: 'Expense',
                      backgroundColor: '#d7d4f5',
                      borderRadius: 20,
                      data: [500, 700, 400, 900, 600],
                  }
              ]
          },
          options: {
              responsive: true,
              plugins: { 
                  legend: { position: 'bottom' },
                  tooltip: {
                      callbacks: {
                          label: function(context) {
                              return `${context.dataset.label}: £${context.parsed.y}`;
                          }
                      }
                  }
              }
          }
      });
  }

  // Budget vs Spending Chart
  const budgetChartCanvas = document.getElementById('budgetChart');
  if (budgetChartCanvas) {
      const ctx = budgetChartCanvas.getContext('2d');
      new Chart(ctx, {
          type: 'bar',
          data: {
              labels: ['Food', 'Transport', 'Utilities', 'Entertainment'],
              datasets: [
                  {
                      label: 'Actual Spending',
                      data: [220, 45, 80, 130],
                      backgroundColor: '#3498db'
                  },
                  {
                      label: 'Budget Goal',
                      data: [200, 100, 80, 0],
                      backgroundColor: '#2ecc71'
                  }
              ]
          },
          options: {
              responsive: true,
              scales: {
                  y: { beginAtZero: true }
              },
              plugins: {
                  tooltip: {
                      callbacks: {
                          label: function(context) {
                              return `${context.dataset.label}: £${context.parsed.y}`;
                          }
                      }
                  }
              }
          }
      });

      // Export button
      document.querySelector('.btn-export')?.addEventListener('click', function() {
          alert('Export functionality would be implemented here');
      });

      // Time filter
      document.getElementById('timePeriod')?.addEventListener('change', function() {
          alert('Filtering for ' + this.value);
      });
  }
}

// Form validation setup
function setupFormValidation() {
  const form = document.querySelector('form');
  if (!form) return;

  const fields = ['title', 'amount', 'category', 'type', 'date'];

  fields.forEach(fieldId => {
      const input = document.getElementById(fieldId);
      if (input) {
          input.addEventListener('input', () => validateField(input));
      }
  });

  form.addEventListener('submit', function(e) {
      let isValid = true;
      fields.forEach(fieldId => {
          const input = document.getElementById(fieldId);
          if (input && !validateField(input)) {
              isValid = false;
          }
      });
      if (!isValid) {
          e.preventDefault();
      }
  });
}

// Field validation
function validateField(input) {
  const value = input.value.trim();
  const errorMessageId = `${input.id}-error`;

  let errorMessage = '';
  if (!value) {
      errorMessage = 'This field is required.';
  } else if (input.id === 'amount' && (isNaN(value) || parseFloat(value) <= 0)) {
      errorMessage = 'Enter a valid amount greater than 0.';
  }

  let errorElement = document.getElementById(errorMessageId);
  if (!errorElement && input.parentElement) {
      errorElement = document.createElement('div');
      errorElement.id = errorMessageId;
      errorElement.classList.add('error-message');
      input.parentElement.appendChild(errorElement);
  }

  if (errorElement) {
      errorElement.textContent = errorMessage;
      errorElement.style.display = errorMessage ? 'block' : 'none';
  }

  return errorMessage === '';
}

// Set default date
function setDefaultDate() {
  const today = new Date().toISOString().split('T')[0];
  const dateInput = document.getElementById('date');
  if (dateInput) {
      dateInput.value = today;
  }
}

// Load data from API
function loadAPIData() {
  // Summary data
  if (document.getElementById("income")) {
      fetch("/api/summary")
          .then(res => res.json())
          .then(data => {
              document.getElementById("income").textContent = `₦${data.income.toFixed(2)}`;
              document.getElementById("expense").textContent = `₦${data.expense.toFixed(2)}`;
              document.getElementById("balance").textContent = `₦${data.balance.toFixed(2)}`;
          })
          .catch(error => console.error('Error loading summary data:', error));
  }

  // Recent transactions
  const tableBody = document.querySelector("#recentTransactions tbody");
  if (tableBody) {
      fetch("/api/transactions")
          .then(res => res.json())
          .then(transactions => {
              tableBody.innerHTML = "";
              transactions.slice(0, 5).forEach(t => {
                  const row = document.createElement("tr");
                  row.innerHTML = `
                      <td>${t.title}</td>
                      <td>${t.category}</td>
                      <td>${t.date}</td>
                      <td>₦${t.amount.toFixed(2)}</td>
                      <td>${t.type}</td>
                  `;
                  tableBody.appendChild(row);
              });
          })
          .catch(error => console.error('Error loading transactions:', error));
  }
}

// Budget goals form setup
function setupBudgetGoalsForm() {
  const budgetForm = document.getElementById('budgetForm');
  const goalList = document.getElementById('goalList');
  
  if (budgetForm && goalList) {
      budgetForm.addEventListener('submit', function(e) {
          e.preventDefault();
          const category = document.getElementById('category').value;
          const amount = parseFloat(document.getElementById('goalAmount').value);
          const date = document.getElementById('goalDate').value;

          if (!category || isNaN(amount)) {
              alert('Please fill all required fields');
              return;
          }

          addGoalToList(category, amount, date);
          updateSummary();
          this.reset();
      });
  }

  // Initialize any existing goals
  updateSummary();
}

// Budget goal functions
function addGoalToList(category, amount, date) {
  const goalList = document.getElementById('goalList');
  if (!goalList) return;

  const li = document.createElement('li');
  li.className = 'goal-item';
  li.innerHTML = `
      <div class="goal-info">
          <h3>${category}</h3>
          <p>$${amount.toFixed(2)} ${date ? '· Target: ' + date : ''}</p>
      </div>
      <div class="goal-actions">
          <button onclick="editGoal(this)"><i class="material-icons">edit</i></button>
          <button onclick="deleteGoal(this)"><i class="material-icons">delete</i></button>
      </div>
  `;
  goalList.appendChild(li);
}

function updateSummary() {
  const goals = document.querySelectorAll('.goal-item');
  let total = 0;
  goals.forEach(goal => {
      const amountText = goal.querySelector('p')?.textContent;
      if (amountText) {
          const amountMatch = amountText.match(/\$([\d.]+)/);
          if (amountMatch) {
              total += parseFloat(amountMatch[1]);
          }
      }
  });
  
  const totalBudgetEl = document.getElementById('totalBudget');
  const activeGoalsEl = document.getElementById('activeGoals');
  
  if (totalBudgetEl) totalBudgetEl.textContent = `$${total.toFixed(2)}`;
  if (activeGoalsEl) activeGoalsEl.textContent = goals.length;
}

// Global functions for goal management
window.deleteGoal = function(button) {
  if (confirm('Are you sure you want to delete this budget goal?')) {
      button.closest('.goal-item')?.remove();
      updateSummary();
  }
};

window.editGoal = function(button) {
  const goalItem = button.closest('.goal-item');
  if (!goalItem) return;

  const category = goalItem.querySelector('h3')?.textContent;
  const amountText = goalItem.querySelector('p')?.textContent;
  const amountMatch = amountText?.match(/\$([\d.]+)/);

  if (category && amountMatch) {
      const amount = parseFloat(amountMatch[1]);
      document.getElementById('category').value = category;
      document.getElementById('goalAmount').value = amount;
      goalItem.remove();
      updateSummary();
  }
};



// To get settings
fetch('/api/settings', {
  method: 'GET',
  headers: {
      'Content-Type': 'application/json',
      'x-access-token': localStorage.getItem('token')  
  }
})
.then(response => response.json())
.then(data => {

  document.getElementById('currency').value = data.currency;
  document.getElementById('theme').value = data.theme;
  // ... etc
});

// To save settings
document.getElementById('save-settings').addEventListener('click', () => {
  const settings = {
      currency: document.getElementById('currency').value,
      theme: document.getElementById('theme').value,
      monthly_budget: parseFloat(document.getElementById('monthly-budget').value),
      email_notifications: document.getElementById('email-notifications').checked,
      push_notifications: document.getElementById('push-notifications').checked,
      budget_alerts: document.getElementById('budget-alerts').checked
  };

  fetch('/api/settings', {
      method: 'PUT',
      headers: {
          'Content-Type': 'application/json',
          'x-access-token': localStorage.getItem('token')  
      },
      body: JSON.stringify(settings)
  })
  .then(response => response.json())
  .then(data => {
      if (data.error) {
          alert('Error: ' + data.error);
      } else {
          alert('Settings saved successfully!');
          
      }
  });
});

$.ajaxSetup({
  beforeSend: function(xhr, settings) {
      if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type)) {
          xhr.setRequestHeader("X-CSRFToken", $('meta[name="csrf-token"]').attr('content'));
      }
  }
});
