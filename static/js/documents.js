// Documents page specific functionality

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Documents page
    setupDocumentsNavigation();
});

function setupDocumentsNavigation() {
    // Smooth scrolling for internal links
    const tocLinks = document.querySelectorAll('a[href^="#"]');
    tocLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
                
                // Update active state in table of contents
                updateActiveTocItem(this);
            }
        });
    });
    
    // Highlight current section in table of contents on scroll
    setupScrollSpy();
}

function updateActiveTocItem(activeLink) {
    // Remove active state from all ToC links
    const tocLinks = document.querySelectorAll('a[href^="#"]');
    tocLinks.forEach(link => {
        link.classList.remove('bg-primary', 'text-white');
        link.classList.add('hover:bg-gray-50');
    });
    
    // Add active state to clicked link
    activeLink.classList.add('bg-primary', 'text-white');
    activeLink.classList.remove('hover:bg-gray-50');
}

function setupScrollSpy() {
    const sections = document.querySelectorAll('div[id]');
    const tocLinks = document.querySelectorAll('a[href^="#"]');
    
    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const id = entry.target.id;
                    const correspondingLink = document.querySelector(`a[href="#${id}"]`);
                    
                    if (correspondingLink) {
                        updateActiveTocItem(correspondingLink);
                    }
                }
            });
        },
        {
            rootMargin: '-20% 0px -70% 0px'
        }
    );
    
    sections.forEach(section => {
        if (section.id) {
            observer.observe(section);
        }
    });
}