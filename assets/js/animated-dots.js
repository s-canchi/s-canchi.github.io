(function () {
  var canvas = document.createElement("canvas");
  canvas.id = "dots-canvas";
  document.getElementById("splash-background").appendChild(canvas);
  var ctx = canvas.getContext("2d");

  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }
  window.addEventListener("resize", resize);
  resize();

  var dots = [];
  var DOTS = 70;
  var radius = 2.1;
  for (var i = 0; i < DOTS; i++) {
    dots.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.36,
      vy: (Math.random() - 0.5) * 0.36,
      r: radius + Math.random() * 1.2
    });
  }

  function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "rgba(255,255,255,0.58)";
    for (var i = 0; i < dots.length; i++) {
      var d = dots[i];
      ctx.beginPath();
      ctx.arc(d.x, d.y, d.r, 0, Math.PI * 2);
      ctx.fill();
      d.x += d.vx;
      d.y += d.vy;
      // Bounce off edges
      if (d.x < 0 || d.x > canvas.width) d.vx *= -1;
      if (d.y < 0 || d.y > canvas.height) d.vy *= -1;
    }
    requestAnimationFrame(animate);
  }
  animate();
})();