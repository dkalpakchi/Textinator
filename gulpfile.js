var gulp = require('gulp'),
    FOLDER = 'node_modules';

gulp.task('bulma:css', function() {
  return gulp.src(FOLDER + '/bulma/css/bulma.min.css')
    .pipe(gulp.dest('static/styles'))
});

gulp.task('bulma-carousel:css', function() {
  return gulp.src(FOLDER + '/bulma-carousel/dist/css/bulma-carousel.min.css')
    .pipe(gulp.dest('static/styles'))
});

gulp.task('bulma-carousel:js', function() {
  return gulp.src(FOLDER + '/bulma-carousel/dist/js/bulma-carousel.min.js')
    .pipe(gulp.dest('static/scripts'))
});

gulp.task('bulma', gulp.series(['bulma:css', 'bulma-carousel:css', 'bulma-carousel:js'], function(done) {
  done();
}));

gulp.task('jquery', function() {
  return gulp.src([FOLDER + '/jquery/dist/jquery.min.js',
                   FOLDER + '/jquery/dist/jquery.min.map'])
    .pipe(gulp.dest('static/scripts'))
});

gulp.task('powertip:css', function() {
  return gulp.src([FOLDER + '/jquery-powertip/dist/css/jquery.powertip.min.css'])
    .pipe(gulp.dest('static/styles'))
});

gulp.task('tooltip:js', function() {
  return gulp.src([FOLDER + '/tooltip.js/dist/tooltip.min.js', FOLDER + '/tooltip.js/dist/tooltip.min.js.map'])
    .pipe(gulp.dest('static/scripts'))
});

gulp.task('fontawesome:css', function() {
  return gulp.src(FOLDER + '/@fortawesome/fontawesome-free/css/all.min.css')
    .pipe(gulp.dest('static/styles/fontawesome'));
});

gulp.task('fontawesome:webfonts', function() {
  return gulp.src(FOLDER + '/@fortawesome/fontawesome-free/webfonts/*')
    .pipe(gulp.dest('static/styles/webfonts'));
})

gulp.task('fontawesome', gulp.series(['fontawesome:css', 'fontawesome:webfonts'], function(done) {
  done();
}));

gulp.task('shepherd:css', function() {
  return gulp.src(FOLDER + '/shepherd.js/dist/css/*')
    .pipe(gulp.dest('static/styles'))
})

gulp.task('shepherd:js', function() {
  return gulp.src(FOLDER + '/shepherd.js/dist/js/shepherd.min.js')
    .pipe(gulp.dest('static/scripts'))
})

gulp.task("shepherd", gulp.series(['shepherd:css', 'shepherd:js'], function(done) {
  done();
}))

gulp.task('d3', function() {
  return gulp.src(FOLDER + '/d3/dist/d3.min.js')
    .pipe(gulp.dest('static/scripts'))
})

gulp.task('default', gulp.series(['bulma', 'jquery', 'fontawesome', 'shepherd', 'd3'], function(done) {
  done();
}));
