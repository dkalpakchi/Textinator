var gulp = require('gulp'),
    FOLDER = 'node_modules';

gulp.task('bulma', function(){
  return gulp.src(FOLDER + '/bulma/css/bulma.min.css')
    .pipe(gulp.dest('static/styles'))
});

gulp.task('jquery', function(){
  return gulp.src([FOLDER + '/jquery/dist/jquery.min.js',
                   FOLDER + '/jquery/dist/jquery.min.map'])
    .pipe(gulp.dest('static/scripts'))
});

gulp.task('default', gulp.series(['bulma', 'jquery'], function(done) {
  done();
}));
