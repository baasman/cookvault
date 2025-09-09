#!/usr/bin/env python3
"""
Flask CLI commands for administrative tasks.
"""

import click
from flask import current_app
from flask.cli import with_appcontext
from datetime import datetime

from app import db
from app.models.payment import Subscription
from app.models.print_order import PrintOrder, PrintSpecification, PrintOrderStatusUpdate


@click.group()
def subscription():
    """Subscription management commands."""
    pass


@subscription.command()
@click.option('--dry-run', is_flag=True, help='Preview changes without committing')
@with_appcontext
def reset_monthly_uploads(dry_run):
    """Reset monthly upload counts for all subscriptions."""
    try:
        # Query all subscriptions with non-zero upload counts
        subscriptions = Subscription.query.filter(
            Subscription.monthly_upload_count > 0
        ).all()
        
        if not subscriptions:
            click.echo("No subscriptions with non-zero upload counts found.")
            return
        
        click.echo(f"Found {len(subscriptions)} subscriptions to reset:")
        
        for sub in subscriptions:
            user = sub.user
            click.echo(f"  - User {user.id} ({user.username}): {sub.monthly_upload_count} uploads")
        
        if dry_run:
            click.echo("\n🧪 DRY RUN: No changes committed to database")
            return
        
        # Reset upload counts
        reset_count = 0
        for sub in subscriptions:
            sub.reset_monthly_uploads()
            reset_count += 1
        
        db.session.commit()
        
        click.echo(f"\n✅ Successfully reset upload counts for {reset_count} subscriptions")
        click.echo(f"Reset timestamp: {datetime.utcnow().isoformat()}")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error resetting monthly uploads: {str(e)}")
        click.echo(f"❌ Error: {str(e)}")
        raise


@subscription.command()
@click.argument('user_id', type=int)
@click.option('--dry-run', is_flag=True, help='Preview changes without committing')
@with_appcontext
def reset_user_uploads(user_id, dry_run):
    """Reset monthly upload count for a specific user."""
    try:
        from app.models.user import User
        
        user = User.query.get(user_id)
        if not user:
            click.echo(f"❌ User with ID {user_id} not found")
            return
        
        subscription = user.get_or_create_subscription()
        current_count = subscription.monthly_upload_count
        
        click.echo(f"User: {user.username} (ID: {user.id})")
        click.echo(f"Current upload count: {current_count}")
        click.echo(f"Subscription tier: {subscription.tier.value}")
        
        if current_count == 0:
            click.echo("Upload count is already at 0")
            return
        
        if dry_run:
            click.echo("\n🧪 DRY RUN: No changes committed to database")
            click.echo(f"Would reset upload count from {current_count} to 0")
            return
        
        subscription.reset_monthly_uploads()
        db.session.commit()
        
        click.echo(f"✅ Successfully reset upload count for {user.username}")
        click.echo(f"Reset timestamp: {datetime.utcnow().isoformat()}")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error resetting user uploads: {str(e)}")
        click.echo(f"❌ Error: {str(e)}")
        raise


@subscription.command()
@with_appcontext
def stats():
    """Show subscription and upload statistics."""
    try:
        # Query subscription statistics
        total_subs = Subscription.query.count()
        premium_subs = Subscription.query.filter_by(tier='premium').count()
        free_subs = total_subs - premium_subs
        
        # Query upload statistics
        total_uploads = db.session.query(db.func.sum(Subscription.monthly_upload_count)).scalar() or 0
        non_zero_uploads = Subscription.query.filter(Subscription.monthly_upload_count > 0).count()
        
        # Get users with highest upload counts
        top_uploaders = Subscription.query.filter(
            Subscription.monthly_upload_count > 0
        ).order_by(
            Subscription.monthly_upload_count.desc()
        ).limit(5).all()
        
        click.echo("📊 Subscription Statistics")
        click.echo("=" * 50)
        click.echo(f"Total subscriptions: {total_subs}")
        click.echo(f"  - Premium: {premium_subs}")
        click.echo(f"  - Free: {free_subs}")
        click.echo(f"\nUpload Statistics (Current Month):")
        click.echo(f"Total uploads this month: {total_uploads}")
        click.echo(f"Users with uploads: {non_zero_uploads}")
        
        if top_uploaders:
            click.echo(f"\nTop uploaders this month:")
            for sub in top_uploaders:
                user = sub.user
                click.echo(f"  - {user.username}: {sub.monthly_upload_count} uploads ({sub.tier.value})")
        
        # Show free tier limit info
        free_limit = current_app.config.get('FREE_TIER_UPLOAD_LIMIT', 10)
        at_limit = Subscription.query.filter(
            Subscription.tier == 'free',
            Subscription.monthly_upload_count >= free_limit
        ).count()
        
        click.echo(f"\nFree Tier Limits:")
        click.echo(f"Upload limit: {free_limit}")
        click.echo(f"Users at/over limit: {at_limit}")
        
    except Exception as e:
        current_app.logger.error(f"Error getting subscription stats: {str(e)}")
        click.echo(f"❌ Error: {str(e)}")
        raise


def init_app(app):
    """Initialize CLI commands with the Flask app."""
    app.cli.add_command(subscription)