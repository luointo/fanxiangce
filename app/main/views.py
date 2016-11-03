# -*-coding: utf-8-*-
import os
from datetime import datetime
from flask import render_template, session, redirect, \
    url_for, flash, abort, request, current_app
from flask_login import login_required, current_user
from werkzeug import secure_filename


from . import main
from .forms import TagForm, WallForm, NormalForm, EditProfileForm, EditProfileAdminForm, CommentForm, EditAlbumForm, GuessNumberForm
from .. import db
from ..models import User, Role, Permission, Album, Photo, Comment, Follow, LikePhoto, LikeAlbum, Message
from wall import wall
from ..decorators import admin_required, permission_required
import random


@main.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')


@main.route('/edit-photo/<int:id>', methods=['GET', 'POST'])
def edit_photo(id):
    album = Album.query.get_or_404(id)
    photos = album.photos.order_by(Photo.order.asc())
    enu_photos = []
    for index, photo in enumerate(photos):
        enu_photos.append((index, photo))
    return render_template('edit_photo.html', album=album, photos=photos, enu_photos=enu_photos)


@main.route('/fast-sort/<int:id>', methods=['GET', 'POST'])
def fast_sort(id):
    album = Album.query.get_or_404(id)
    photos = album.photos.order_by(Photo.order.asc())
    enu_photos = []
    for index, photo in enumerate(photos):
        enu_photos.append((index, photo))
    return render_template('fast_sort.html', album=album, photos=photos, enu_photos=enu_photos)


@main.route('/edit-album/<int:id>', methods=['GET', 'POST'])
def edit_album(id):
    album = Album.query.get_or_404(id)
    form = EditAlbumForm()
    if form.validate_on_submit():
        album.title=form.title.data
        album.about=form.about.data
        album.asc_order=form.asc_order.data
        album.privacy=form.privacy.data
        album.can_comment=form.can_comment.data
        album.author=current_user._get_current_object()
        print form.asc_order.data
        print form.privacy.data
        print form.can_comment.data
        db.session.add(album)
        flash(u'更改已保存。', 'success')
        return redirect(url_for('.album', id=id))
    form.title.data = album.title
    form.about.data = album.about
    form.asc_order.data = album.asc_order
    form.can_comment.data = album.can_comment
    form.privacy.data = album.privacy
    return render_template('edit_album.html', form=form, album=album)


@main.route('/save-edit/<int:id>', methods=['GET', 'POST'])
def save_edit(id):
    album = Album.query.get_or_404(id)
    photos = album.photos
    for photo in photos:
        photo.about = request.form[str(photo.id)]
        photo.order = request.form["order-" + str(photo.id)]
        db.session.add(photo)
    album.cover = request.form["cover"]
    db.session.add(album)
    db.session.commit()
    flash(u'更改已保存。', 'success')
    return redirect(url_for('.album', id=id))


@main.route('/save-photo-edit/<int:id>', methods=['GET', 'POST'])
def save_photo_edit(id):
    photo = Photo.query.get_or_404(id)
    album = photo.album
    photo.about = request.form["about"]
    album.cover = request.form["cover"]
    db.session.add(photo)
    db.session.add(album)
    db.session.commit()
    flash(u'更改已保存。', 'success')
    return redirect(url_for('.photo', id=id))


@main.route('/save-sort/<int:id>', methods=['GET', 'POST'])
def save_sort(id):
    album = Album.query.get_or_404(id)
    photos = album.photos
    for photo in photos:
        photo.order = request.form["order-" + str(photo.id)]
        db.session.add(photo)
    db.session.commit()
    flash(u'更改已保存。', 'success')
    return redirect(url_for('.album', id=id))


@main.route('/user/<username>', methods=['GET', 'POST'])
def user(username):
    user = User.query.filter_by(username=username).first()
    form = CommentForm()
    if user is None:
        abort(404)
    albums = user.albums.order_by(Album.timestamp.desc()).all()
    album_count = len(albums)
    photo_count = sum([len(album.photos.order_by(Photo.timestamp.asc()).all()) for album in albums])
    photo_likes = user.photo_likes.order_by(LikePhoto.timestamp.desc()).all()
    album_likes = user.album_likes.order_by(LikeAlbum.timestamp.desc()).all()
    photo_likes = [{'photo': like.like_photo, 'timestamp': like.timestamp, 'path': like.like_photo.path} for like in
                   photo_likes[:2]]
    album_likes = [{'album': like.like_album, 'photo': like.like_album.photos,
                    'timestamp': like.timestamp, 'cover': like.like_album.cover} for like in album_likes[:2]]

    if form.validate_on_submit() and current_user.is_authenticated:
        comment = Message(body=form.body.data,
                          user=user,
                          author=current_user._get_current_object())
        db.session.add(comment)
        flash(u'你的评论已经发表。', 'success')
        return redirect(url_for('.user', username=username))
    comments = user.messages.order_by(Message.timestamp.asc()).all()
    return render_template('user.html', form=form, user=user, photo_likes=photo_likes, album_likes=album_likes,
                           albums=albums, comments=comments, album_count=album_count, photo_count=photo_count)


@main.route('/user/<username>/albums')
def albums(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    albums = user.albums.order_by(Album.timestamp.desc()).all()
    if current_user != user and current_user.is_followed_by(user) == False:
        albums = user.albums.query.filter_by(privacy='11').order_by(Album.timestamp.desc()).all()
    elif current_user != user and current_user.is_followed_by(user) == True:
        albums = user.albums.query.filter_by(privacy='10' or '11').order_by(Album.timestamp.desc()).all()
    else:
        albums = user.albums.order_by(Album.timestamp.desc()).all()
    album_count = len(albums)
    return render_template('albums.html', user=user, albums=albums, album_count=album_count)


@main.route('/user/<username>/likes')
def likes(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    photo_likes = user.photo_likes.order_by(LikePhoto.timestamp.desc()).all()
    album_likes = user.album_likes.order_by(LikeAlbum.timestamp.desc()).all()
    photo_likes = [{'photo': like.like_photo, 'timestamp': like.timestamp, 'path':like.like_photo.path} for like in photo_likes]
    album_likes = [{'album': like.like_album, 'photo': like.like_album.photos,
                    'timestamp': like.timestamp, 'cover':like.like_album.cover} for like in album_likes]
    return render_template('likes.html', user=user, photo_likes=photo_likes, album_likes=album_likes)


@main.route('/album/<int:id>')
def album(id):
    album = Album.query.get_or_404(id)
    error_type = {'10': u'仅好友可见', '00': u'仅自己可见'}
    if current_user != album.author and album.privacy != '11':
        if current_user.is_followed_by(album.author) == False or \
                                current_user.is_followed_by(album.author) == False and \
                                album.privacy == '00':
            return render_template('privacy_error.html', error_msg=error_type[album.privacy])

    page = request.args.get('page', 1, type=int)
    pagination = album.photos.order_by(Photo.order.asc()).paginate(
        page, per_page=20, error_out=False
    )
    photos = pagination.items

    if current_user.is_authenticated:
        user = User.query.filter_by(username=current_user.username).first()
        likes = user.photo_likes.order_by(LikePhoto.timestamp.asc()).all()
        likes = [{'id': like.like_photo, 'timestamp': like.timestamp, 'path': like.like_photo.path} for like in likes]
        like_list = [like['path'] for like in likes]
    else:
        likes = ""
        like_list = []

    if current_user.is_authenticated:
        is_liked = album.is_liked_by(current_user)
    else:
        is_liked = False

    if album.type == 1:
        files = []
        for photo in photos:
            files.append(photo.path)
        html = wall()
        return render_template('wall.html', album=album, html=html)
    return render_template('album.html', album=album, photos=photos, pagination=pagination,
                           like_list=like_list, likes=likes, is_liked=is_liked)


@main.route('/photo/<int:id>', methods=['GET', 'POST'])
def photo(id):
    photo = Photo.query.get_or_404(id)
    album = photo.album
    if current_user != album.author and album.privacy != '11':
        if current_user.is_followed_by(album.author) == False or \
                                current_user.is_followed_by(album.author) == True and \
                                album.privacy == '00':
            abort(404)

    photo_sum = len(list(album.photos))
    form = CommentForm()
    photo_index = [p.id for p in album.photos.order_by(Photo.order.asc())].index(photo.id) + 1
    if current_user.is_authenticated:
        user = User.query.filter_by(username=current_user.username).first()
        likes = user.photo_likes.order_by(LikePhoto.timestamp.desc()).all()
        likes = [{'id': like.like_photo, 'timestamp': like.timestamp, 'path': like.like_photo.path, 'liked':like.photo_liked} for like in likes]
        like_list = [like['path'] for like in likes]
    else:
        likes = ""
        like_list = []

    if form.validate_on_submit() and current_user.is_authenticated:
        comment = Comment(body=form.body.data,
                          photo=photo,
                          author=current_user._get_current_object())
        db.session.add(comment)
        flash(u'你的评论已经发表。', 'success')
        return redirect(url_for('.photo', id=photo.id))
    page = request.args.get('page', 1, type=int)
    pagination = photo.comments.order_by(Comment.timestamp.asc()).paginate(
        page, per_page=current_app.config['FANXIANGCE_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    amount = len(comments)
    if amount != 0:
        amount = range(amount)
    return render_template('photo.html', form=form, album=album, amount=amount,
                           like_list=like_list, photo=photo, pagination=pagination,
                           comments=comments, photo_index=photo_index, photo_sum=photo_sum)


@main.route('/photo/n/<int:id>')
def photo_next(id):
    "reditrct to next imgae"
    photo_now = Photo.query.get_or_404(id)
    album = photo_now.album
    photos = album.photos.order_by(Photo.order.asc())
    position = list(photos).index(photo_now) + 1
    if position == len(list(photos)):
        position = None
        flash(u'已经是最后一张了。', 'info')
        return redirect(url_for('.photo', id=id))
    photo = photos[position]
    return redirect(url_for('.photo', id=photo.id))

@main.route('/photo/p/<int:id>')
def photo_previous(id):
    "reditrct to previous imgae"
    photo_now = Photo.query.get_or_404(id)
    album = photo_now.album
    photos = album.photos.order_by(Photo.order.asc())
    position = list(photos).index(photo_now) - 1
    if position == -1:
        position = None
        flash(u'已经是第一张了。', 'info')
        return redirect(url_for('.photo', id=id))
    photo = photos[position]
    return redirect(url_for('.photo', id=photo.id))

@main.route('/edit-profile', methods=['GET', 'POST'])
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.status = form.status.data
        current_user.location = form.location.data
        current_user.website = form.website.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user)
        flash(u'你的资料已经更新。', 'success')
        return redirect(url_for('.user', username=current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.website.data = current_user.website
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)

@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.website = form.website.data
        user.about_me = form.about_me.data
        db.session.add(current_user)
        flash(u'资料已经更新。', 'success')
        return redirect(url_for('.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role
    form.name.data = user.name
    form.location.data = user.location
    form.website.data = user.website
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user)


@main.route('/create-tag', methods=['GET', 'POST'])
def tag():
    flash(u'目前只是测试阶段，仅支持标签云相册，暂不提供永久存储。不好意思>_<')
    form = TagForm()
    app = current_app._get_current_object()
    if form.validate_on_submit():
        title = form.title.data
        sub_title = form.sub_title.data
        theme = form.theme.data
        pro_attachment = request.files.getlist('pro_attachment1')
        for upload in pro_attachment:
            filename = upload.filename.rsplit("/")[0]
            destination = os.path.join(app.config['UPLOADED_PHOTOS_DEST'], filename)
            print "Accept incoming file:", filename
            print "Save it to:", destination
            upload.save(destination)
        # glue()
        return render_template('tag_album.html', title=title, sub_title=sub_title)
    return render_template('create/tag.html', form=form)


@main.route('/create-wall', methods=['GET', 'POST'])
def wall():
    form = WallForm()
    from flask_uploads import UploadSet, configure_uploads, IMAGES
    app = current_app._get_current_object()
    photos = UploadSet('photos', IMAGES)
    if form.validate_on_submit(): # current_user.can(Permission.CREATE_ALBUMS) and
        if request.method == 'POST' and 'photo' in request.files:
            filename=[]
            for img in request.files.getlist('photo'):
                photos.save(img)
                url = photos.url(img.filename)
                filename.append(url.replace("%20", "_"))
        title = form.title.data
        about = form.about.data
        author = current_user._get_current_object()
        album = Album(title=title,
        about=about, cover=filename[0], type=1,
        author = current_user._get_current_object())
        db.session.add(album)

        for file in filename:
            photo = Photo(path=file, album=album)
            db.session.add(photo)
        db.session.commit()
        return redirect(url_for('.album', id=album.id))
    return render_template('create/wall.html', form=form)

@main.route('/create-normal', methods=['GET', 'POST'])
@login_required
def normal():
    from flask_uploads import UploadSet, configure_uploads, IMAGES
    app = current_app._get_current_object()
    photos = UploadSet('photos', IMAGES)
    form = NormalForm()
    if form.validate_on_submit(): # current_user.can(Permission.CREATE_ALBUMS) and
        if request.method == 'POST' and 'photo' in request.files:
            filename=[]
            for img in request.files.getlist('photo'):
                photos.save(img)
                url = photos.url(img.filename)
                url = url.replace("%20", "_")
                url = url.replace("%28", "")
                url = url.replace("%29", "")
                filename.append(url)
        title = form.title.data
        about = form.about.data
        author = current_user._get_current_object()
        album = Album(title=title,
        about=about, cover=filename[0],
        author = current_user._get_current_object())
        db.session.add(album)

        for file in filename:
            photo = Photo(path=file, album=album,
                          author=current_user._get_current_object())
            db.session.add(photo)
        db.session.commit()
        return redirect(url_for('.album', id=album.id))
    return render_template('create/normal.html', form=form)

# @main.route('/edit-album/<int:id>')
# def edit_album(id):
#     album = Album.query.filter_by(id=id).first()
#     form = EditAlbumForm()
#     if form.validate_on_submit():
#         title = form.title.data
#         about = form.about.data
#         private = form.private.data
#         comment = form.comment.data
#     form.title.data = album.title
#     form.about.data = album.about
#     form.private.data = album.private
#     form.comment.data = album.comment




@main.route('/follow/<username>')
@login_required
# @permission_required(Permission.FOLLOW)
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    if current_user.is_following(user):
        flash('You are already following this user.')
        return redirect(url_for('.user', username=username))
    current_user.follow(user)
    flash('You are now following %s.' % username)
    return redirect(url_for('.user', username=username))


@main.route('/unfollow/<username>')
@login_required
# @permission_required(Permission.FOLLOW)
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    if not current_user.is_following(user):
        flash('You are not following this user.')
        return redirect(url_for('.user', username=username))
    current_user.unfollow(user)
    flash('You are not following %s anymore.' % username)
    return redirect(url_for('.user', username=username))


@main.route('/followers/<username>')
def followers(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followers.paginate(
        page, per_page=10 ,#current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.follower, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title=u"的关注者",
                           endpoint='.followers', pagination=pagination,
                           follows=follows)


@main.route('/followed-by/<username>')
def followed_by(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followed.paginate(
        page, per_page=10, #current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.followed, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title=u"关注的人",
                           endpoint='.followed_by', pagination=pagination,
                           follows=follows)


@main.route('/photo/like/<id>')
@login_required
#@permission_required(Permission.FOLLOW)# todo follow > like
def like_photo(id):
    photo = Photo.query.filter_by(id=id).first()
    album = photo.album
    if photo is None:
        flash(u'无效的图片。', 'warning')
        return redirect(url_for('.album', id=album))
    if current_user.is_like_photo(photo):
        current_user.unlike_photo(photo)
        redirect(url_for('.photo', id=id))
    else:
        current_user.like_photo(photo)
    return redirect(url_for('.photo', id=id))

@main.route('/album/like/<id>')
@login_required
#@permission_required(Permission.FOLLOW)# todo follow > like
def like_album(id):
    album = Album.query.filter_by(id=id).first()
    if album is None:
        flash(u'无效的相册。', 'warning')
        return redirect(url_for('.albums', username=album.author.username))
    if current_user.is_like_album(album):
        current_user.unlike_album(album)
        flash(u'喜欢已取消。', 'success')
        redirect(url_for('.album', id=id))
    else:
        current_user.like_album(album)
        flash(u'相册已经添加到你的喜欢里了。', 'success')
    return redirect(url_for('.album', id=id))

@main.route('/photo/unlike/<id>')
@login_required
#@permission_required(Permission.FOLLOW)# todo follow > like
def unlike_photo(id):
    photo = Photo.query.filter_by(id=id).first()
    if photo is None:
        flash(u'无效的图片。', 'warning')
        return redirect(url_for('.likes', username=current_user.username))
    if current_user.is_like_photo(photo):
        current_user.unlike_photo(photo)
    return (''), 204

@main.route('/album/unlike/<id>')
@login_required
#@permission_required(Permission.FOLLOW)# todo follow > like
def unlike_album(id):
    album = Album.query.filter_by(id=id).first()
    if album is None:
        flash(u'无效的相册。', 'warning')
        return redirect(url_for('.likes', username=current_user.username))
    if current_user.is_like_album(album):
        current_user.unlike_album(album)
    return (''), 204

def redirect_url(default='index'):
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

# usage: return redirect(redirect_url())

@main.route('/delete/photo/<id>')
@login_required
def delete_photo(id):
    photo = Photo.query.filter_by(id=id).first()
    album = photo.album
    if photo is None:
        flash(u'无效的操作。', 'warning')
        return redirect(url_for('.index', username=current_user.username))
    if current_user.username != photo.author.username:
        abort(403)
    db.session.delete(photo)
    db.session.commit()
    flash(u'删除成功。', 'success')
    return redirect(url_for('.album', id=album.id))

@main.route('/delete/edit-photo/<id>')
@login_required
def delete_edit_photo(id):
    photo = Photo.query.filter_by(id=id).first()
    album = photo.album
    if photo is None:
        flash(u'无效的操作。', 'warning')
        return redirect(url_for('.index', username=current_user.username))
    if current_user.username != photo.author.username:
        abort(403)
    db.session.delete(photo)
    db.session.commit()
    return (''), 204


@main.route('/delete/album/<id>')
@login_required
def delete_album(id):
    album = Album.query.filter_by(id=id).first()
    if album is None:
        flash(u'无效的操作。', 'warning')
        return redirect(url_for('.index', username=current_user.username))
    if current_user.username != album.author.username:
        abort(403)
    db.session.delete(album)
    db.session.commit()
    flash(u'删除成功。', 'success')
    return redirect(url_for('.albums', username=album.author.username))