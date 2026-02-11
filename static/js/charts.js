const ctx = document.getElementById('statChart').getContext('2d');
const myChart = new Chart(ctx, {
    type: 'bar',
    data: {
        labels: ['Robot', 'Humain'],
        datasets: [{
            label: 'Cartes Jouées',
            data: [0, 0],
            backgroundColor: ['#3b82f6', '#f97316']
        }]
    },
    options: {
        responsive: true,
        plugins: { legend: { labels: { color: 'white' } } },
        scales: { y: { ticks: { color: 'white' } }, x: { ticks: { color: 'white' } } }
    }
});