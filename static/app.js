const apiBase = '/api';

async function fetchChain() {
  const res = await fetch(`${apiBase}/blockchain/chain`);
  const data = await res.json();
  document.getElementById('chain').textContent = JSON.stringify(data, null, 2);
}

async function mine() {
  const res = await fetch(`${apiBase}/blockchain/mine`);
  const data = await res.json();
  alert(data.message || 'Mined');
  fetchChain();
}

document.getElementById('viewChain').addEventListener('click', fetchChain);
document.getElementById('mineBlock').addEventListener('click', mine);

document.getElementById('txForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const sender = document.getElementById('sender').value || 'anonymous';
  const recipient = document.getElementById('recipient').value || 'recipient';
  const amount = parseFloat(document.getElementById('amount').value) || 0;
  let dataVal = document.getElementById('data').value.trim();
  let jsonData = null;
  try { if (dataVal) jsonData = JSON.parse(dataVal); } catch (err) { alert('Invalid JSON data'); return; }

  const res = await fetch(`${apiBase}/blockchain/transactions/new`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sender, recipient, amount, data: jsonData }),
  });
  const body = await res.json();
  alert(body.message || JSON.stringify(body));
  fetchChain();
});

// load initial chain on start
fetchChain();
