
    // Vote visualization code
    function createVoteChart(containerId, data, options) {
        const container = document.getElementById(containerId);
        const width = container.offsetWidth;
        const height = 120;
        
        // Create SVG
        const svg = d3.select(container)
            .append('svg')
            .attr('width', width)
            .attr('height', height)
            .attr('class', 'vote-chart');
            
        // Calculate dimensions
        const margin = {top: 20, right: 20, bottom: 20, left: 20};
        const chartWidth = width - margin.left - margin.right;
        const chartHeight = height - margin.top - margin.bottom;
        
        // Create scales
        const xScale = d3.scaleLinear()
            .domain([0, data.total.yea + data.total.nay])
            .range([0, chartWidth]);
            
        // Create groups for votes
        const g = svg.append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);
            
        // Draw Democratic votes
        g.append('rect')
            .attr('class', 'vote-bar dem-yea')
            .attr('x', 0)
            .attr('y', 20)
            .attr('width', xScale(data.by_party.democratic.yea.length))
            .attr('height', 30)
            .attr('fill', '#2166AC')
            .attr('opacity', 0.9);
            
        // Draw Republican votes
        g.append('rect')
            .attr('class', 'vote-bar rep-nay')
            .attr('x', xScale(data.by_party.democratic.yea.length))
            .attr('y', 20)
            .attr('width', xScale(data.by_party.republican.nay.length))
            .attr('height', 30)
            .attr('fill', '#B2182B')
            .attr('opacity', 0.9);
            
        // Add vote counts
        g.append('text')
            .attr('class', 'vote-count dem-count')
            .attr('x', xScale(data.by_party.democratic.yea.length / 2))
            .attr('y', 40)
            .attr('text-anchor', 'middle')
            .attr('fill', 'white')
            .text(data.by_party.democratic.yea.length);
            
        g.append('text')
            .attr('class', 'vote-count rep-count')
            .attr('x', xScale(data.by_party.democratic.yea.length + data.by_party.republican.nay.length / 2))
            .attr('y', 40)
            .attr('text-anchor', 'middle')
            .attr('fill', 'white')
            .text(data.by_party.republican.nay.length);
            
        // Add labels
        g.append('text')
            .attr('class', 'vote-label')
            .attr('x', 10)
            .attr('y', 15)
            .attr('fill', '#2166AC')
            .text('Democrats');
            
        g.append('text')
            .attr('class', 'vote-label')
            .attr('x', width - margin.right - 70)
            .attr('y', 15)
            .attr('fill', '#B2182B')
            .text('Republicans');
    }

    // Initialize visualizations when document is ready
    document.addEventListener('DOMContentLoaded', function() {
        const houseData = ${json.dumps(vote_data['house'])};
        const senateData = ${json.dumps(vote_data['senate'])};
        
        createVoteChart('house-vote-chart', houseData);
        createVoteChart('senate-vote-chart', senateData);
        
        // Initialize member lists
        initializeMemberLists(houseData, senateData);
    });

    function initializeMemberLists(houseData, senateData) {
        // Add click handlers for member list toggles
        document.querySelectorAll('.member-list-toggle').forEach(toggle => {
            toggle.addEventListener('click', function() {
                const target = this.getAttribute('data-target');
                const list = document.getElementById(target);
                list.classList.toggle('expanded');
                this.classList.toggle('active');
            });
        });
    }
    