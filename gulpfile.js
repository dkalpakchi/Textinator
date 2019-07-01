var gulp = require('gulp'),
    FOLDER = 'node_modules';

gulp.task('bulma', function() {
  return gulp.src(FOLDER + '/bulma/css/bulma.min.css')
    .pipe(gulp.dest('static/styles'))
});

gulp.task('jquery', function() {
  return gulp.src([FOLDER + '/jquery/dist/jquery.min.js',
                   FOLDER + '/jquery/dist/jquery.min.map'])
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

gulp.task('default', gulp.series(['bulma', 'jquery', 'fontawesome'], function(done) {
  done();
}));
