async function loadMessages() {
  const res = await fetch('/messages');
  const data = await res.json();
  const list = document.getElementById('messages');
  list.innerHTML = '';
  data.forEach(([id, name, msg]) => {
    const li = document.createElement('li');
    li.textContent = `${name}: ${msg}`;
    list.appendChild(li);
  });
}

document.getElementById('msgForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const name = document.getElementById('name').value;
  const message = document.getElementById('message').value;

  await fetch('/messages', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, message }),
  });

  document.getElementById('name').value = '';
  document.getElementById('message').value = '';
  loadMessages();
});

loadMessages();
