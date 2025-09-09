document.addEventListener("DOMContentLoaded", function() {
  var links = document.querySelectorAll('a[href]');
  links.forEach(function(link) {
    var href = link.getAttribute('href');
    if (
      href &&
      !href.startsWith('#') &&
      !href.startsWith('/') &&
      !href.startsWith(window.location.origin) &&
      (href.startsWith('http://') || href.startsWith('https://'))
    ) {
      link.setAttribute('target', '_blank');
      link.setAttribute('rel', 'noopener noreferrer');
    }
  });
});
