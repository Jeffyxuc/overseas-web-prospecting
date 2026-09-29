(() => {
  'use strict';
  const d = window.DEMO;
  if (!d || !Array.isArray(d.items)) {
    document.getElementById('tagline').textContent = 'This concept needs its business content.';
    return;
  }
  const set = (id, value) => { document.getElementById(id).textContent = value; };
  const themes = {
    catalog: {label: 'The collection', title: 'Good things, thoughtfully made.', flow: 'A simpler way to pick up.', description: 'Explore the selection, choose a favourite and preview a pickup request.', field: 'Pickup window', options: ['Morning · 9–11', 'Midday · 11–13', 'Afternoon · 14–16']},
    booking: {label: 'Our services', title: 'A little time, just for you.', flow: 'Find a moment that fits.', description: 'Choose a service and explore a clearer appointment journey.', field: 'Preferred time', options: ['Morning', 'Afternoon', 'Evening']},
    quote: {label: 'How we help', title: 'The right help, close to home.', flow: 'Start with what you need.', description: 'Choose a service and preview the first step toward a tailored quote.', field: 'Project scope', options: ['Small project', 'Medium project', 'Larger project']}
  };
  const t = themes[d.kind] || themes.catalog;
  document.title = d.name + ' — independent website concept';
  document.documentElement.dataset.kind = d.kind;
  set('brand', d.name); set('footer-brand', d.name); set('tagline', d.tagline); set('intro', d.intro); set('address', d.address);
  set('collection-link', t.label); set('collection-title', d.collection_title || t.title); set('flow-title', t.flow); set('flow-description', t.description); set('detail-label', t.field);
  const heroAction = document.querySelector('.hero-copy > .pill');
  heroAction.firstChild.textContent = d.kind === 'catalog' ? 'Find your favourite ' : d.kind === 'booking' ? 'Explore our services ' : 'Find the right help ';
  if (d.eyebrow) set('eyebrow', d.eyebrow);
  if (d.note) set('hero-note', d.note);
  const choices = document.getElementById('choice');
  const detail = document.getElementById('detail');
  t.options.forEach(value => { const opt = document.createElement('option'); opt.textContent = value; opt.value = value; detail.append(opt); });
  d.items.forEach((item, index) => {
    const card = document.createElement('article'); card.className = 'card';
    const number = document.createElement('span'); number.className = 'card-number'; number.textContent = String(index + 1).padStart(2, '0');
    const title = document.createElement('h3'); title.textContent = item.title;
    const desc = document.createElement('p'); desc.textContent = item.description;
    const button = document.createElement('button'); button.type = 'button'; button.className = 'text-button'; button.textContent = 'Explore this option ↗';
    button.addEventListener('click', () => { choices.value = String(index); document.getElementById('experience').scrollIntoView({behavior: 'smooth'}); choices.focus({preventScroll: true}); });
    card.append(number, title, desc, button); document.getElementById('cards').append(card);
    const opt = document.createElement('option'); opt.value = String(index); opt.textContent = item.title; choices.append(opt);
  });
  const date = document.getElementById('date');
  const today = new Date();
  const localDay = `${today.getFullYear()}-${String(today.getMonth()+1).padStart(2,'0')}-${String(today.getDate()).padStart(2,'0')}`;
  date.min = localDay;
  document.getElementById('demo-form').addEventListener('submit', event => {
    event.preventDefault();
    if (!event.currentTarget.reportValidity()) return;
    const item = d.items[Number(choices.value)];
    if (!item || date.value < localDay) return;
    const summary = document.getElementById('summary');
    summary.textContent = `Demo request: ${item.title} · ${date.value} · ${detail.value}. This is a preview only. Nothing has been sent, reserved or charged.`;
    summary.hidden = false;
  });
})();
